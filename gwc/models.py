from django.db import models
from django.utils import timezone
from decimal import Decimal
from accounts.models import UserProfile


class GWCGroup(models.Model):
    """
    GWC Groups - Users pool together to reach 120M minimum
    Once 120M is reached, others can join with any amount
    """
    name = models.CharField(max_length=200, help_text="Group name")
    description = models.TextField(blank=True, help_text="Group description")
    
    # Financial targets
    target_amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('120000000'),
        help_text="Minimum amount required (120M)"
    )
    total_contributed = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total amount contributed by all members"
    )
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Group is active and accepting members")
    is_complete = models.BooleanField(
        default=False, 
        help_text="Group has reached minimum target (120M)"
    )
    
    # Group creator
    created_by = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE,
        related_name='created_gwc_groups',
        help_text="User who created this group"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When group reached 120M")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "GWC Group"
        verbose_name_plural = "GWC Groups"
    
    def __str__(self):
        return f"{self.name} - UGX {self.total_contributed:,.0f} / {self.target_amount:,.0f}"
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.target_amount <= 0:
            return 0
        return min((self.total_contributed / self.target_amount) * 100, 100)
    
    @property
    def remaining_amount(self):
        """Amount remaining to reach target"""
        return max(self.target_amount - self.total_contributed, Decimal('0.00'))
    
    @property
    def member_count(self):
        """Number of members in group"""
        return self.members.count()
    
    def check_and_update_status(self):
        """Check if group has reached 120M and update status"""
        if not self.is_complete and self.total_contributed >= self.target_amount:
            self.is_complete = True
            self.completed_at = timezone.now()
            self.save(update_fields=['is_complete', 'completed_at'])
            return True
        return False


class GWCGroupMember(models.Model):
    """
    Members of a GWC Group and their contributions
    One user can only be in one group
    """
    group = models.ForeignKey(
        GWCGroup, 
        on_delete=models.CASCADE, 
        related_name='members'
    )
    user_profile = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE,
        related_name='gwc_group_memberships'
    )
    contribution_amount = models.DecimalField(
        max_digits=14, 
        decimal_places=2,
        help_text="Amount this member contributed"
    )
    
    # Status
    is_leader = models.BooleanField(
        default=False,
        help_text="Is this member the group leader/creator"
    )
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['group', 'user_profile']]  # One user per group
        ordering = ['-joined_at']
        verbose_name = "GWC Group Member"
        verbose_name_plural = "GWC Group Members"
    
    def __str__(self):
        return f"{self.user_profile.user.get_username()} - {self.group.name} (UGX {self.contribution_amount:,.0f})"
    
    def save(self, *args, **kwargs):
        # Set leader if this is the creator
        if not self.pk and self.group.created_by == self.user_profile:
            self.is_leader = True
        super().save(*args, **kwargs)


class GWCContribution(models.Model):
    """
    Individual contribution transactions to GWC groups
    Tracks each contribution separately for history
    """
    group = models.ForeignKey(
        GWCGroup,
        on_delete=models.CASCADE,
        related_name='contributions'
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='gwc_contributions'
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Contribution amount"
    )
    
    # Transaction reference
    receipt_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Transaction receipt number"
    )
    
    # Timestamps
    contributed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-contributed_at']
        verbose_name = "GWC Contribution"
        verbose_name_plural = "GWC Contributions"
    
    def __str__(self):
        return f"{self.user_profile.user.get_username()} - UGX {self.amount:,.0f} to {self.group.name}"
