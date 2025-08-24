from django.core.management.base import BaseCommand
from django.utils import timezone
from savings_52_weeks.models import Investment


class Command(BaseCommand):
    help = 'Check and update maturity status for all investments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all fixed investments
        fixed_investments = Investment.objects.filter(status='fixed')
        self.stdout.write(f"Found {fixed_investments.count()} fixed investments")
        
        matured_investments = []
        for investment in fixed_investments:
            if investment.is_matured:
                matured_investments.append(investment)
                if not dry_run:
                    investment.status = 'matured'
                    investment.save(update_fields=['status'])
        
        if matured_investments:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'Would update' if dry_run else 'Updated'} {len(matured_investments)} investments to matured status"
                )
            )
            
            for investment in matured_investments:
                user = investment.user_profile.user
                self.stdout.write(
                    f"  - {user.get_full_name() or user.username}: "
                    f"UGX {investment.amount_invested:,.0f} matured on {investment.maturity_date}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("No investments have matured yet"))
        
        # Show summary
        total_fixed = Investment.objects.filter(status='fixed').count()
        total_matured = Investment.objects.filter(status='matured').count()
        
        self.stdout.write(f"\nSummary:")
        self.stdout.write(f"  Fixed investments: {total_fixed}")
        self.stdout.write(f"  Matured investments: {total_matured}")
        self.stdout.write(f"  Total investments: {total_fixed + total_matured}")
