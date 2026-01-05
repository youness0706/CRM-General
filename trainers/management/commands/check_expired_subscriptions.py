
from django.core.management.base import BaseCommand
from django.utils import timezone
from trainers.models import OrganizationInfo
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Check for expired subscriptions and send notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-emails',
            action='store_true',
            help='Send email notifications to expired organizations',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        send_emails = options['send_emails']
        
        # Get all organizations
        organizations = OrganizationInfo.objects.all()
        
        stats = {
            'total': 0,
            'active': 0,
            'expiring_soon': 0,
            'in_grace': 0,
            'expired': 0,
            'emails_sent': 0
        }
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f'فحص اشتراكات الجمعيات - {today}'))
        self.stdout.write("="*60 + "\n")
        
        for org in organizations:
            stats['total'] += 1
            days_left = org.days_until_expiration()
            
            if days_left is None:
                continue
            
            # Update organization status
            was_active = org.is_active
            org.check_and_update_status()
            
            # Categorize
            if org.is_expired():
                stats['expired'] += 1
                status_symbol = self.style.ERROR('✗')
                status_text = self.style.ERROR(f'منتهي ({abs(days_left)} يوم)')
                
                # Deactivated?
                if was_active and not org.is_active:
                    self.stdout.write(
                        self.style.WARNING(f'  → تم إلغاء تفعيل: {org.name}')
                    )
                
                # Send email notification
                if send_emails:
                    self._send_expiration_email(org, days_left)
                    stats['emails_sent'] += 1
                    
            elif org.is_in_grace_period():
                stats['in_grace'] += 1
                status_symbol = self.style.WARNING('⚠')
                status_text = self.style.WARNING(f'فترة سماح ({abs(days_left)} يوم)')
                
            elif days_left <= 7:
                stats['expiring_soon'] += 1
                status_symbol = self.style.WARNING('!')
                status_text = self.style.WARNING(f'قرب الانتهاء ({days_left} يوم)')
                
                # Send reminder email
                if send_emails and days_left in [7, 3, 1]:
                    self._send_reminder_email(org, days_left)
                    stats['emails_sent'] += 1
                    
            else:
                stats['active'] += 1
                status_symbol = self.style.SUCCESS('✓')
                status_text = self.style.SUCCESS(f'نشط ({days_left} يوم)')
            
            # Print organization status
            self.stdout.write(
                f'{status_symbol} {org.name:30} → {status_text}'
            )
        
        # Print summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS('ملخص الفحص:'))
        self.stdout.write("="*60)
        self.stdout.write(f'إجمالي الجمعيات: {stats["total"]}')
        self.stdout.write(self.style.SUCCESS(f'✓ نشطة: {stats["active"]}'))
        self.stdout.write(self.style.WARNING(f'! قرب الانتهاء: {stats["expiring_soon"]}'))
        self.stdout.write(self.style.WARNING(f'⚠ فترة سماح: {stats["in_grace"]}'))
        self.stdout.write(self.style.ERROR(f'✗ منتهية: {stats["expired"]}'))
        
        if send_emails:
            self.stdout.write(f'📧 رسائل مرسلة: {stats["emails_sent"]}')
        
        self.stdout.write("="*60 + "\n")

    def _send_expiration_email(self, org, days_overdue):
        """Send email notification for expired subscription"""
        subject = f'⚠️ اشتراك {org.name} منتهي'
        
        message = f"""
السلام عليكم،

نود إعلامكم أن اشتراك جمعية {org.name} قد انتهى منذ {abs(days_overdue)} يوم.

تفاصيل الاشتراك:
- تاريخ الانتهاء: {org.subscription_end_date}
- الحالة: منتهي

للحفاظ على خدماتكم، يرجى تجديد الاشتراك في أقرب وقت ممكن.

للتجديد أو الاستفسار، يرجى التواصل معنا.

شكراً لكم،
فريق الدعم
        """
        
        try:
            # Get admin emails for this organization
            admin_emails = org.staff_set.filter(is_admin=True).values_list('email', flat=True)
            admin_emails = [email for email in admin_emails if email]
            
            if admin_emails:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=False,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'  📧 تم إرسال بريد إلى {len(admin_emails)} مسؤول')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ فشل إرسال البريد: {str(e)}')
            )

    def _send_reminder_email(self, org, days_left):
        """Send reminder email before expiration"""
        subject = f'⏰ تذكير: اشتراك {org.name} سينتهي خلال {days_left} يوم'
        
        message = f"""
السلام عليكم،

نود تذكيركم أن اشتراك جمعية {org.name} سينتهي خلال {days_left} يوم فقط.

تفاصيل الاشتراك:
- تاريخ الانتهاء: {org.subscription_end_date}
- الأيام المتبقية: {days_left}

للحفاظ على استمرارية خدماتكم، يرجى تجديد الاشتراك قبل انتهائه.

للتجديد أو الاستفسار، يرجى التواصل معنا.

شكراً لكم،
فريق الدعم
        """
        
        try:
            admin_emails = org.staff_set.filter(is_admin=True).values_list('email', flat=True)
            admin_emails = [email for email in admin_emails if email]
            
            if admin_emails:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=False,
                )
        except Exception as e:
            pass  # Silent failure for reminders


# To run this command:
# python manage.py check_expired_subscriptions
# python manage.py check_expired_subscriptions --send-emails
