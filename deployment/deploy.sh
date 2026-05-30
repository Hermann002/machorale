#!/bin/bash
set -euo pipefail

# Lancé par le workflow GHA depuis /home/hermann/ma_chorale/
# Le scp a déjà placé compose.yml, compose.prod.yml ici
# .env existe (créé manuellement, jamais écrasé par scp)

COMPOSE_FILES="-f compose.yml -f compose.prod.yml"

# TAG est fourni par le workflow (github.ref_name). On REFUSE de deployer
# sans tag explicite : sinon compose retombe sur ':latest' (reconstruit
# uniquement sur main) et redeploie une vieille image en silence.
: "${TAG:?TAG non defini — refus de deployer (eviterait de tirer ':latest' perime)}"
export TAG
echo "[0/6] Image ciblee : tag '$TAG'"

echo "[1/6] Detection de l'image en prod..."
CURRENT_IMAGE=$(docker inspect --format='{{.Config.Image}}' ma_chorale_web 2>/dev/null || echo "")

if [ -z "$CURRENT_IMAGE" ]; then
  echo "   Premier deploiement detecte (aucun conteneur 'web' existant)."
else
  echo "   Image actuelle sauvegardee : $CURRENT_IMAGE"
  echo "$CURRENT_IMAGE" > .deploy_previous_image
fi

echo "[2/6] Pull de la nouvelle image..."
docker compose $COMPOSE_FILES pull

echo "[3/6] Taches pre-demarrage (migrations)..."
docker compose $COMPOSE_FILES run --rm web python manage.py migrate || {
  echo "Migrations echouees. Annulation immediate..."
  rm -f .deploy_previous_image
  exit 1
}

echo "[4/6] Demarrage du nouveau conteneur..."
docker compose $COMPOSE_FILES up -d --remove-orphans

echo "[5/6] Verification de la sante (max 20 tentatives, 5s d'intervalle)..."
MAX_RETRIES=20
RETRY=0
HEALTHY=false
while [ $RETRY -lt $MAX_RETRIES ]; do
  if docker compose $COMPOSE_FILES ps web --format "{{.Status}}" | grep -q "healthy"; then
    HEALTHY=true
    break
  fi
  echo "En attente... ($((RETRY+1))/$MAX_RETRIES)"
  sleep 5
  RETRY=$((RETRY + 1))
done

if [ "$HEALTHY" = false ]; then
  echo "Healthcheck echoue. Declenchement du rollback..."

  if [ -f ".deploy_previous_image" ]; then
    PREVIOUS_IMAGE=$(cat .deploy_previous_image)
    NEW_IMAGE=$(docker compose $COMPOSE_FILES config | awk '/^  web:/,/^  [a-z]/' | grep 'image:' | head -1 | awk '{print $2}')

    echo "Restauration de : $PREVIOUS_IMAGE"
    # Re-tag de l'ancienne image sous le nom courant pour que compose la reprenne
    docker tag "$PREVIOUS_IMAGE" "$NEW_IMAGE"
    docker compose $COMPOSE_FILES up -d --no-deps web --force-recreate

    echo "Rollback termine. L'ancienne version est de nouveau en ligne."
  else
    echo "Impossible de rollback (premier deploiement). Verifie les logs manuellement."
  fi

  rm -f .deploy_previous_image
  exit 1
fi

echo "[6/6] Nettoyage des anciennes images (uniquement si succes)..."
docker image prune -f --filter "until=24h"
rm -f .deploy_previous_image
echo "Deploiement termine avec succes."
