"""Fill locale/en/LC_MESSAGES/django.po with English translations.

Strategy:
1. Entries whose msgid is ALREADY in English (because the source used
   `gettext_lazy("English text")` in models.py): copy msgid → msgstr.
2. Entries with French msgids: look up in the explicit FR_TO_EN dict.
3. Anything left untranslated stays empty and msgfmt --statistics will report it.

Run AFTER makemessages -l en. Idempotent.
"""
from __future__ import annotations

from pathlib import Path

import polib


PO_PATH = Path(__file__).resolve().parent.parent / "locale" / "en" / "LC_MESSAGES" / "django.po"


# English msgids — source already in English; msgstr == msgid.
EN_PASS_THROUGH = {
    "French", "English",
    "Chorale", "Movement", "Association",
    "Income", "Expense",
    "Practice", "Meeting", "Concert", "Attendance", "Other",
    "Expenses (XAF)", "Income (XAF)",
    "Warning", "Fine", "Suspension",
    "Only for fines",
    "Payment deadline (fine) or end date (suspension)",
    "Lift date — null = sanction active",
    "Payment made", "Sanction applied", "Member added", "Member removed", "Report",
    "Member", "Secretary", "Treasurer", "Censor", "Super Chorale Admin",
    "Single", "Married", "Divorced", "Widowed",
    "Student", "Computer scientist", "Nurse", "Teacher", "Engineer", "Doctor", "Lawyer",
    "Chorale concerned by the event",
    "User who triggered the event",
    "Date and time of the event",
    "Event type",
    "Detailed description of the event",
    "Short description for notifications",
    "Additional comment (e.g., reason for a sanction)",
    "Type of the related object (e.g., Contribution, Sanction)",
    "ID of the related object",
    "Contextual data (old value, new value, etc.)",
    "User's IP address at the time of the action",
    "User agent of the browser/device",
    "Indicates whether the event is considered important for notifications",
    "Amount expected per member",
    "Total chorale target (optional)",
    # View messages already written in English in source
    "Account created successfully! Please verify your email.",
    "You're already logged in. Please log out first to switch accounts.",
    "Invalid credentials. Please try again.",
    "Invalid username or password.",
    "User not found! Please register first.",
    "OTP code has expired. Please request a new code.",
    "Email verified successfully!",
    "Email is already verified. Please log in.",
    "No OTP record found. Please request a new code.",
    "Rate limit reached, please wait 1 minute and retry.",
    "OTP code resent successfully! Please check your email.",
    "User not found.",
    "Rate limit exceeded, please wait before trying again.",
    "Password reset link sent! Please check your email.",
    "No account found with that email address.",
    "Please enter a valid email address.",
    "Invalid or expired password reset link.",
    "Invalid password reset link.",
    "Invalid password reset request.",
    "Your password has been reset successfully! You can now log in.",
    "You need to verify your email before creating a chorale.",
    "You already manage a chorale. Redirecting to your dashboard.",
    "Your chorale has been created successfully!",
    "An error occurred while creating the chorale.",
    "You do not have permission to modify roles.",
    "The role of %(name)s has been updated.",
    "You do not have permission to create an event.",
    "The event has been created successfully.",
    "You do not have permission to modify an event.",
    "The event has been updated successfully.",
    "Contribution type created.",
    "Contribution type updated.",
    'Contribution "%(title)s" deleted.',
    "Payment recorded.",
    "Cash flow entry recorded.",
    "Cash flow entry updated.",
    "%(count)d absence recorded for \"%(title)s\".",
    "%(count)d absences recorded for \"%(title)s\".",
    "Absence updated.",
    "Absence deleted.",
    "Sanction recorded.",
    "Sanction updated.",
    "Sanction lifted.",
    "Sanction deleted.",
    "You are not authorized to assign this role.",
    "%(name)s has been added as %(role)s.",
    "An error occurred while adding the member.",
    "Dashboard",
    "Chorale members",
    "Events calendar",
    "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun",
    "Confirm Password", "Email", "Password", "New Password", "Confirm New Password",
    "Username", "OTP Code",
    "Les mots de passe ne correspondent pas.",
    "Invalid username or password.",
    "No account found with this email.",
    "The two password fields didn't match.",
}


# French → English manual translation map. Add entries as templates are wrapped.
FR_TO_EN = {
    "Nom du groupe": "Group name",
    "Ex: Chorale Harmonie": "E.g. Harmonie Choir",
    "Type de groupe": "Group type",
    "Description": "Description",
    "Une brève description de la chorale": "A short description of the choir",
    "Date de création": "Founding date",
    "Lieu": "Location",
    "Ex: Paris, France": "E.g. Paris, France",
    "Logo de la chorale": "Choir logo",
    "Le nom du groupe est requis.": "The group name is required.",
    "Ce nom de chorale est déjà utilisé.": "This choir name is already in use.",
    "La date de création ne peut pas être dans le futur.": "The founding date cannot be in the future.",
    "Le lieu doit contenir au moins 2 caractères.": "The location must be at least 2 characters long.",
    "Le fichier ne doit pas dépasser 5MB.": "The file must not exceed 5MB.",
    "Format de fichier non autorisé. Formats acceptés : JPG, PNG, GIF.": "File format not allowed. Accepted formats: JPG, PNG, GIF.",
    "Slogan": "Slogan",
    "Email de contact": "Contact email",
    "Téléphone de contact": "Contact phone",
    "Fréquence des réunions": "Meeting frequency",
    "Hebdomadaire": "Weekly",
    "Bihebdomadaire": "Bi-weekly",
    "Mensuelle": "Monthly",
    "Annuelle": "Yearly",
    "Le slogan ne doit pas dépasser 255 caractères.": "The slogan must not exceed 255 characters.",
    "L'adresse email est trop longue.": "The email address is too long.",
    "Le numéro de téléphone doit contenir au moins 7 chiffres.": "The phone number must contain at least 7 digits.",
    "Le numéro de téléphone est trop long.": "The phone number is too long.",
    "Fréquence de réunion invalide.": "Invalid meeting frequency.",
    "Titre de l'événement": "Event title",
    "Description de l'événement": "Event description",
    "Lieu de l'événement": "Event location",
    "La date de l'événement ne peut pas être dans le passé.": "The event date cannot be in the past.",
    "Le fichier doit être inférieur à 10MB.": "The file must be less than 10MB.",
    "Email du membre": "Member email",
    "Entrez l'email du membre à ajouter": "Enter the email of the member to add",
    "Nom du membre": "Member last name",
    "Ex: Jean Dupont": "E.g. John Smith",
    "Prénom du membre": "Member first name",
    "Numéro de téléphone": "Phone number",
    "Ex: 01 23 45 67 89": "E.g. 01 23 45 67 89",
    "Rôle dans la chorale": "Role in the choir",
    "Ex: Cotisation mensuelle Janvier 2026": "E.g. Monthly contribution January 2026",
    "Objectif total (optionnel)": "Total target (optional)",
    "À quoi sert cette cotisation ?": "What is this contribution for?",
    "Le montant doit être strictement positif.": "The amount must be strictly positive.",
    "Un type de cotisation portant ce titre existe déjà.": "A contribution type with this title already exists.",
    "Référence, mode de paiement... (optionnel)": "Reference, payment method... (optional)",
    "Ex: Don pour le concert, Achat partitions": "E.g. Concert donation, Score purchase",
    "Détails (optionnel)": "Details (optional)",
    "Rencontre": "Meeting",
    "Membres absents": "Absent members",
    "Raison commune (optionnel)": "Common reason (optional)",
    "Ex: Maladie, voyage...": "E.g. Illness, travel...",
    "Absence(s) justifiée(s)": "Justified absence(s)",
    "Raison de l'absence": "Reason for absence",
    "Pourquoi cette sanction ?": "Why this sanction?",
    "Montant (amende uniquement)": "Amount (fine only)",
    "Une amende requiert un montant strictement positif.": "A fine requires a strictly positive amount.",
    # Navbar
    "Admin Portal": "Admin Portal",
    "Cotisations": "Contributions",
    "Paiements": "Payments",
    "Membres": "Members",
    "Calendrier": "Calendar",
    "Absences": "Absences",
    "Sanctions": "Sanctions",
    "Finances": "Finances",
    "Evénements": "Events",
    "Activités": "Activities",
    "Ajouter un membre": "Add a member",
    "Déconnexion": "Log out",
    # Header
    "Rechercher...": "Search...",
    "Administrateur de chorale": "Choir administrator",
    # Base demo
    "Mode démo — vos données seront supprimées après 2h.": "Demo mode — your data will be deleted after 2 hours.",
    "Créer un vrai compte →": "Create a real account →",
    # Landing navbar / header
    "Fonctionnalités": "Features",
    "Tarifs": "Pricing",
    "À propos": "About",
    "Connexion": "Sign in",
    "Essai gratuit": "Free trial",
    "Tableau de bord": "Dashboard",
    "Créer une chorale": "Create a choir",
    # Landing footer
    "La solution dédiée aux groupes chrétiens pour une gestion harmonieuse et simplifiée.": "The dedicated solution for Christian groups for harmonious and simplified management.",
    "Produit": "Product",
    "Sécurité": "Security",
    "Mises à jour": "Updates",
    "Société": "Company",
    "Blog": "Blog",
    "Témoignages": "Testimonials",
    "Contact": "Contact",
    "Légal": "Legal",
    "Conditions d'utilisation": "Terms of use",
    "Confidentialité": "Privacy",
    "Mentions légales": "Legal notice",
    "© 2024 ChorusSérénité. Tous droits réservés.": "© 2024 ChorusSérénité. All rights reserved.",
    "Français": "French",
    # Login page
    "Contact support": "Contact support",
    "Harmonie": "Harmony",
    "Gérez les activités, les finances et la fréquentation de votre chorale de manière fluide dans une seule plateforme unifiée.": "Manage your choir's activities, finances and attendance smoothly in one unified platform.",
    "ma chorale Pro v1": "ma chorale Pro v1",
    "Se connecter": "Sign in",
    "Bienvenue ! Veuillez entrer vos identifiants.": "Welcome! Please enter your credentials.",
    "Se souvenir de moi": "Remember me",
    "Mot de passe oublié ?": "Forgot your password?",
    "Nouveau ici ?": "New here?",
    "Créer un compte": "Create an account",
    "© 2026 machorale. Tous droits réservés.": "© 2026 machorale. All rights reserved.",
    # Register page
    "Inscription": "Sign up",
    "Aide": "Help",
    "Simplifiez la gestion de votre <span class=\"text-primary\">groupe chrétien</span>.": "Simplify the management of your <span class=\"text-primary\">Christian group</span>.",
    "Données sécurisées": "Secure data",
    "Vos données sont protégées par un cryptage de bout en bout. La confidentialité des membres est notre priorité absolue.": "Your data is protected by end-to-end encryption. Member privacy is our top priority.",
    "Organisation simplifiée": "Simplified organization",
    "Centralisez vos partitions, répétitions et membres en un seul endroit. Ne perdez plus jamais de temps sur le planning.": "Centralize your scores, rehearsals and members in one place. Never waste time on scheduling again.",
    "Transparence totale": "Total transparency",
    "Suivi clair des finances et de l'assiduité pour toute la chorale. Une gestion saine pour un chœur en harmonie.": "Clear tracking of finances and attendance for the whole choir. Healthy management for a choir in harmony.",
    "« machorale a transformé la façon dont nous organisons nos répétitions. C'est simple, intuitif et tout le monde est enfin sur la même page. »": '"machorale has transformed how we organize our rehearsals. It is simple, intuitive and everyone is finally on the same page."',
    "Directeur technique": "Technical director",
    "Créer votre compte chorale": "Create your choir account",
    "Déjà membre ?": "Already a member?",
    "Connectez-vous ici": "Sign in here",
    "Utilisez au moins 8 caractères avec des lettres et chiffres.": "Use at least 8 characters with letters and digits.",
    "J'accepte les <a class=\"text-primary hover:underline font-medium\" href=\"#\">conditions d'utilisation</a> et la <a class=\"text-primary hover:underline font-medium\" href=\"#\">politique de confidentialité</a>.": "I accept the <a class=\"text-primary hover:underline font-medium\" href=\"#\">terms of use</a> and the <a class=\"text-primary hover:underline font-medium\" href=\"#\">privacy policy</a>.",
    "Créer mon compte": "Create my account",
    "Besoin d'aide pour configurer votre chorale ?": "Need help setting up your choir?",
    "Contactez notre équipe de support": "Contact our support team",
    # Verify email
    "Vérification Email - Choir Management": "Email Verification - Choir Management",
    "Vérifiez votre adresse email": "Verify your email address",
    "Un code de vérification à 6 chiffres a été envoyé à l'adresse associée à votre compte. Veuillez le saisir ci-dessous.": "A 6-digit verification code has been sent to the address associated with your account. Please enter it below.",
    "Confirmer": "Confirm",
    "Vous n'avez pas reçu de code ?": "Did not receive a code?",
    "Renvoyer le code": "Resend the code",
    # Reset password
    "Réinitialisation du mot de passe": "Password reset",
    "Gestion de chorale": "Choir management",
    "Entrez l'adresse email afin de recevoir les instructions pour réinitialiser votre mot de passe.": "Enter the email address to receive instructions to reset your password.",
    "Envoyer les instructions": "Send instructions",
    "Choir Management © 2024 • Sécurisé par AES-256": "Choir Management © 2024 • Secured by AES-256",
    "Azure Choir": "Azure Choir",
    "Vocal Ensemble": "Vocal Ensemble",
    "Cliquez sur le bouton ci-dessous pour confirmer la réinitialisation de votre compte.": "Click the button below to confirm the reset of your account.",
    "Nouveau mot de passe": "New password",
    "Confirmer le mot de passe": "Confirm password",
    "Réinitialiser le mot de passe": "Reset password",
    "Retour à la connexion": "Back to sign in",
    # Wizard
    "Étape 3 sur 3": "Step 3 of 3",
    "Configurez votre chorale": "Configure your choir",
    "Précédent": "Previous",
    "Terminer la configuration": "Finish setup",
    "En continuant, vous acceptez nos": "By continuing, you agree to our",
    "Conditions d'Utilisation": "Terms of Use",
    "Étape 2 sur 3": "Step 2 of 3",
    "Créer le profil de votre chorale": "Create your choir profile",
    "Continuer la configuration": "Continue setup",
    "Vous pourrez ajouter des membres à l'étape suivante.": "You can add members in the next step.",
    # Dashboard
    "Vue d'ensemble": "Overview",
    "Content de te revoir. Voici ce qui s'est passé aujourd'hui avec la chorale.": "Welcome back. Here is what happened today with the choir.",
    "Créer un événement": "Create an event",
    "nouveaux": "new",
    "Total membres": "Total members",
    "%(n)s actif": "%(n)s active",
    "Date de la dernière réunion": "Last meeting date",
    "Solde actuel": "Current balance",
    "Sanctions en cours": "Pending sanctions",
    "%(n)s sanction": "%(n)s sanction",
    "Activités récentes": "Recent activities",
    "Voir plus": "See more",
    "Ajouté au fonds général • XAF %(amount)s": "Added to general fund • XAF %(amount)s",
    "Aucune activité récente enregistrée.": "No recent activity recorded.",
    "Prochaines répétitions": "Upcoming rehearsals",
    "Aucun événement de pratique à venir pour le moment.": "No upcoming practice events for now.",
    "Actions rapides": "Quick actions",
    "Exporter le registre des présences": "Export attendance log",
    "Envoyer un email à tous les membres": "Email all members",
    "Imprimer la fiche de la chorale": "Print choir sheet",
    # Events
    "Calendrier des événements": "Events calendar",
    "Consultez la liste des événements et les prochaines dates importantes.": "View the list of events and upcoming important dates.",
    "Ajouter un événement": "Add an event",
    "Mois précédent": "Previous month",
    "Mois suivant": "Next month",
    "Suivant": "Next",
    "événement": "event",
    "Prochains événements": "Upcoming events",
    "Aucun événement à venir dans ce mois.": "No upcoming events this month.",
    # User-side wrapped strings already in source
    "Ce nom d'utilisateur est déjà utilisé.": "This username is already taken.",
    "Cet email est déjà utilisé.": "This email is already in use.",
    "Nom d'utilisateur": "Username",
    "Mot de passe": "Password",
    # Phone validation
    "Le numéro doit être au format international, ex: +237 77 123 45 67": "The number must be in international format, e.g. +237 77 123 45 67",
    # Home page
    "Solution pour chorales": "Solution for choirs",
    "Gérez votre chorale avec <span class=\"text-[#e0ad53]\">sérénité</span>": "Manage your choir with <span class=\"text-[#e0ad53]\">serenity</span>",
    "Une plateforme moderne tout-en-un pour simplifier la gestion de vos membres, le suivi de vos finances et l'organisation de vos répétitions.": "A modern all-in-one platform to simplify member management, finance tracking and rehearsal scheduling.",
    "Commencer Gratuitement": "Get Started for Free",
    "Voir la démo": "Watch the demo",
    "Rejoint par plus de 500 chorales ce mois-ci": "Joined by over 500 choirs this month",
    "Ils nous font confiance": "They trust us",
    "Outils de gestion": "Management tools",
    "Tout ce dont vous avez besoin pour votre chorale": "Everything you need for your choir",
    "Des outils puissants et intuitifs conçus spécifiquement pour les besoins des ensembles vocaux modernes au sein de l'Église.": "Powerful and intuitive tools designed specifically for the needs of modern vocal ensembles in the Church.",
    "Suivi des Membres": "Member Tracking",
    "Annuaire numérique détaillé avec répartition par pupitres (Soprano, Alto, Ténor, Basse) et gestion des contacts.": "Detailed digital directory with section breakdown (Soprano, Alto, Tenor, Bass) and contact management.",
    "Livre Financier": "Financial Ledger",
    "Suivi rigoureux des cotisations, dons et dépenses. Transparence totale pour les membres et le bureau.": "Rigorous tracking of contributions, donations and expenses. Total transparency for members and the board.",
    "Comptes-rendus": "Reports",
    "Archivage centralisé des procès-verbaux de réunions et résumés d'activités hebdomadaires.": "Centralized archive of meeting minutes and weekly activity summaries.",
    "Présences": "Attendance",
    "Pointage rapide lors des répétitions et prestations. Statistiques d'assiduité individuelles et collectives.": "Quick check-in for rehearsals and performances. Individual and collective attendance statistics.",
    "Nos Tarifs": "Our Pricing",
    "Une offre adaptée à votre ensemble": "A plan tailored to your ensemble",
    "Choisissez le plan qui correspond le mieux à la taille et aux besoins de votre ministère musical.": "Choose the plan that best fits the size and needs of your musical ministry.",
    "Gratuit": "Free",
    "Pour les petites chorales et débuter sereinement.": "For small choirs starting out with peace of mind.",
    "/mois": "/month",
    "Jusqu'à 15 membres": "Up to 15 members",
    "Suivi des présences": "Attendance tracking",
    "Livre financier basique": "Basic financial ledger",
    "Commencer": "Get started",
    "Populaire": "Popular",
    "Pro": "Pro",
    "Fonctionnalités complètes pour une gestion optimale.": "Full features for optimal management.",
    "Membres illimités": "Unlimited members",
    "Comptabilité avancée": "Advanced accounting",
    "Rapports automatisés": "Automated reports",
    "Espace de stockage partitions": "Sheet music storage",
    "Support prioritaire": "Priority support",
    "Choisir Pro": "Choose Pro",
    "Église": "Church",
    "Pour la gestion multi-groupes au sein d'une paroisse.": "For multi-group management within a parish.",
    "Jusqu'à 5 chorales/groupes": "Up to 5 choirs/groups",
    "Administration centralisée": "Centralized administration",
    "Tableau de bord de district": "District dashboard",
    "Formation personnalisée": "Personalized training",
    "Contacter Sales": "Contact Sales",
    "Prêt à transformer l'organisation de votre chorale ?": "Ready to transform your choir's organization?",
    "Rejoignez les centaines de chefs de chœur qui utilisent déjà ChorusSérénité pour se concentrer sur l'essentiel : la louange.": "Join hundreds of choir directors who already use ChorusSérénité to focus on what matters: worship.",
    "Commencer l'essai gratuit": "Start the free trial",
    "Demander une démo": "Request a demo",
    "Pas de carte de crédit requise • Installation en 5 minutes": "No credit card required • Setup in 5 minutes",
}


def main() -> None:
    if not PO_PATH.exists():
        raise SystemExit(f"Not found: {PO_PATH}. Run makemessages first.")

    po = polib.pofile(str(PO_PATH))
    pass_through = 0
    translated = 0
    skipped = 0

    for entry in po:
        if not entry.msgid:
            continue  # header entry

        if entry.msgid_plural:
            # ngettext entry: translate singular and plural
            singular = FR_TO_EN.get(entry.msgid) or (entry.msgid if entry.msgid in EN_PASS_THROUGH else None)
            plural = FR_TO_EN.get(entry.msgid_plural) or (entry.msgid_plural if entry.msgid_plural in EN_PASS_THROUGH else None)
            if singular is not None and plural is not None:
                entry.msgstr_plural = {0: singular, 1: plural}
                translated += 1
            else:
                skipped += 1
            continue

        if entry.msgid in EN_PASS_THROUGH:
            entry.msgstr = entry.msgid
            pass_through += 1
        elif entry.msgid in FR_TO_EN:
            entry.msgstr = FR_TO_EN[entry.msgid]
            translated += 1
        else:
            skipped += 1

    po.save()
    total = len(po)
    print(f"Total entries: {total}")
    print(f"  pass-through (already EN): {pass_through}")
    print(f"  translated FR → EN:        {translated}")
    print(f"  skipped (no translation):  {skipped}")


if __name__ == "__main__":
    main()
