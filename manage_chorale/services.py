from django.core.cache import cache
from .models import Contribution, Chorale
from manage_users.models import MemberContribution

class DjangoContributionRepo:
    def get_by_title(self, contrib_ref):
        return Contribution.objects.get(title=contrib_ref)

class DjangoMemberContributionRepo:
    def create(self, **kwargs):
        return MemberContribution.objects.create(**kwargs)
    
class ContributionService:
    def __init__(self, contribution_repo: DjangoContributionRepo, member_contrib_repo: DjangoMemberContributionRepo):
        self.contribution_repo = contribution_repo
        self.member_contrib_repo = member_contrib_repo

    def save_contribution(self, member_id, contribution_ref, amount=None):
        contribution = self.contribution_repo.get_by_title(contribution_ref)
        if amount is None:
            amount = contribution.amount

        self.member_contrib_repo.create(
            member_id=member_id,
            contribution_ref=contribution_ref,
            amount=amount
        )


def get_dashboard_stats(chorale_id, timeout=60):
    cache_key = f"dashboard_stats:{chorale_id}"
    stats = cache.get(cache_key)
    if stats is not None:
        return stats

    chorale = Chorale.objects.filter(pk=chorale_id).first()
    if not chorale:
        return {"error": "Chorale not found"}

    stats = {
        "total_members": chorale.members.count(),
    }
    cache.set(cache_key, stats, timeout)
    return stats
