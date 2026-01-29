from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField
from django.utils.timezone import now
from django.utils.text import slugify
import os
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.core.validators import FileExtensionValidator




class OrganizationInfo(models.Model):
    """Main organization/tenant model"""
    name = models.CharField(max_length=255, verbose_name='اسم الجمعية')
    slug = models.SlugField(unique=True, verbose_name='المعرف')
    description = models.TextField(blank=True, verbose_name='الوصف')
    established_date = models.DateField(blank=True, null=True, verbose_name='تاريخ التأسيس')
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الإيجار')
    phone_number = models.CharField(max_length=15, blank=True, verbose_name='رقم الهاتف')
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني')
    
    # Subscription fields
    subscription_tier = models.CharField(
        max_length=20,
        choices=[('free', 'مجاني'), ('basic', 'أساسي'), ('premium', 'متميز')],
        default='free',
        verbose_name='نوع الاشتراك'
    )
    max_trainers = models.IntegerField(default=50, verbose_name='الحد الأقصى للمتدربين')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    is_active = models.BooleanField(default=True, verbose_name='ناشط')
    # Subscription status and dates
    SUBSCRIPTION_STATUS_CHOICES = [
        ('trial', 'تجريبي'),
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('suspended', 'معلق'),
    ]
    
    SUBSCRIPTION_PERIOD_CHOICES = [
        ('1m', 'شهر واحد'),
        ('3m', 'ثلاثة أشهر'),
    ]
    
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default='trial',
        verbose_name='حالة الاشتراك'
    )
    trial_start = models.DateField(blank=True, null=True, verbose_name='بداية التجربة')
    trial_end = models.DateField(blank=True, null=True, verbose_name='نهاية التجربة')
    subscription_start = models.DateField(blank=True, null=True, verbose_name='بداية الاشتراك')
    subscription_end = models.DateField(blank=True, null=True, verbose_name='نهاية الاشتراك')
    subscription_start_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="تاريخ بداية الاشتراك"
    )
    subscription_end_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="تاريخ نهاية الاشتراك"
    )
    grace_period_days = models.IntegerField(
        default=7,
        verbose_name="فترة السماح "
    )
    subscription_period = models.CharField(
        max_length=2,
        choices=SUBSCRIPTION_PERIOD_CHOICES,
        blank=True,
        null=True,
        verbose_name='مدةالاشتراك'
    )
    last_payment_date = models.DateField(blank=True, null=True, verbose_name='تاريخ آخر دفعة')
    location = models.CharField(max_length=255, blank=True, verbose_name='الموقع')
    datepay = models.DateField(default=timezone.now, verbose_name='تاريخ دفع الايجار')
    class Meta:
        verbose_name = 'جمعية'
        verbose_name_plural = 'الجمعيات'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.pk and not self.trial_start:
            self.start_trial()
        super().save(*args, **kwargs)
    
    # Properties
    @property
    def is_on_trial(self):
        """Check if organization is currently on trial"""
        if self.subscription_status != 'trial':
            return False
        if not self.trial_end:
            return False
        return now().date() <= self.trial_end
    
    @property
    def is_subscription_active(self):
        """Check if organization has an active paid subscription"""
        if self.subscription_status != 'active':
            return False
        if not self.subscription_end:
            return False
        return now().date() <= self.subscription_end
    
    @property
    def is_subscription_expired(self):
        """Check if subscription has expired"""
        if self.subscription_status == 'trial':
            if self.trial_end:
                return now().date() > self.trial_end
            return False
        elif self.subscription_status == 'active':
            if self.subscription_end:
                return now().date() > self.subscription_end
            return False
        return self.subscription_status == 'expired'
    
    @property
    def days_remaining(self):
        """Calculate days remaining in current subscription period"""
        today = now().date()
        
        if self.subscription_status == 'trial' and self.trial_end:
            delta = (self.trial_end - today).days
            return max(0, delta)
        elif self.subscription_status == 'active':
            # Try subscription_end_date first, then fall back to subscription_end
            end_date = self.subscription_end_date or self.subscription_end
            if end_date:
                delta = (end_date - today).days
                return max(0, delta)
        
        return 0
    
    # Methods
    def start_trial(self, trial_days=7):
        """Start a free trial period"""
        self.subscription_status = 'trial'
        self.trial_start = now().date()
        self.trial_end = self.trial_start + timedelta(days=trial_days)
        # Also set subscription_end_date for consistency with expiration check logic
        self.subscription_end_date = self.trial_end
        self.subscription_start = None
        self.subscription_end = None
        self.subscription_period = None
        self.last_payment_date = None
        self.save()
    
    def activate_subscription(self, period, amount, user):
        """Activate a paid subscription"""
        if period not in ['1m', '3m']:
            raise ValueError("Period must be '1m' or '3m'")
        
        today = now().date()
        
        # Set subscription dates
        self.subscription_status = 'active'
        self.subscription_start = today
        self.subscription_start_date = today
        self.subscription_period = period
        self.last_payment_date = today
        
        # Calculate end date
        if period == '1m':
            self.subscription_end = today + relativedelta(months=1)
        elif period == '3m':
            self.subscription_end = today + relativedelta(months=3)
        
        # Also set subscription_end_date for consistency
        self.subscription_end_date = self.subscription_end
                
        # Clear trial dates
        self.trial_start = None
        self.trial_end = None

        
        self.save()
        
        # Create payment record
        OrganizationPayment.objects.create(
            organization=self,
            amount=amount,
            period=period,
            payment_date=today,
            activated_by=user
        )
    
    def expire_subscription_if_needed(self):
        """Update status based on current dates"""
        today = now().date()
        
        if self.subscription_status == 'trial':
            if self.trial_end and today > self.trial_end:
                self.subscription_status = 'expired'
                self.save()
        
        elif self.subscription_status == 'active':
            if self.subscription_end and today > self.subscription_end:
                self.subscription_status = 'expired'
                self.save()
    
    @property
    def days_until_expiration(self):
        """Calculate days remaining until subscription expires"""
        # Use subscription_end_date if available, otherwise fall back to subscription_end
        end_date = self.subscription_end_date or self.subscription_end
        
        if not end_date:
            return None
        
        today = timezone.now().date()
        delta = end_date - today
        return delta.days
    def is_in_grace_period(self):
        """Check if organization is in grace period"""
        days_left = self.days_until_expiration
        if days_left is None:
            return False
        return 0 > days_left >= -self.grace_period_days

    def is_expired(self):
        """Check if subscription has expired (past grace period)"""
        days_left = self.days_until_expiration
        if days_left is None:
            return False
        return days_left < -self.grace_period_days

    def get_subscription_status_display(self):
        """Get human-readable subscription status with color coding"""
        days_left = self.days_until_expiration
        
        if days_left is None:
            return {
                'text': 'غير محدد',
                'class': 'warning',
                'days': None
            }
        elif days_left > 30:
            return {
                'text': 'نشط',
                'class': 'success',
                'days': days_left
            }
        elif days_left > 7:
            return {
                'text': f'{days_left} يوم متبقي',
                'class': 'info',
                'days': days_left
            }
        elif days_left > 0:
            return {
                'text': f'تحذير: {days_left} يوم متبقي',
                'class': 'warning',
                'days': days_left
            }
        elif self.is_in_grace_period():
            return {
                'text': f'فترة سماح: متأخر {abs(days_left)} يوم',
                'class': 'danger',
                'days': days_left
            }
        else:
            return {
                'text': 'منتهي',
                'class': 'danger',
                'days': days_left
            }

    def check_and_update_status(self):
        """
        Check subscription status and update is_active flag
        Call this periodically or in middleware
        """
        if self.is_expired():
            self.is_active = False
            self.save()
            return False
        return True


class OrganizationPayment(models.Model):
    """
    Tracks subscription payments for organizations
    Automatically updates organization subscription dates when payment is added
    """
    organization = models.ForeignKey(
        'OrganizationInfo', 
        on_delete=models.CASCADE, 
        related_name='subscription_payments'
    )
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    duration_months = models.IntegerField(
        default=1,
        help_text="عدد الأشهر التي يغطيها هذا الدفع"
    )
    payment_method = models.CharField(
        max_length=50,
        choices=[
            ('cash', 'نقداً'),
            ('bank_transfer', 'تحويل بنكي'),
            ('card', 'بطاقة'),
            ('check', 'شيك'),
            ('other', 'أخرى'),
        ],
        default='cash'
    )
    period = models.CharField(
        max_length=50,
        default='monthly',  # ← This fixes the error!
        choices=[
            ('monthly', 'شهري'),
            ('quarterly', 'ربع سنوي'),
            ('semi_annual', 'نصف سنوي'),
            ('annual', 'سنوي'),
            ('custom', 'مخصص'),
        ],
        verbose_name="فترة",
    )
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    processed_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="تمت المعالجة بواسطة"
    )
    
    # Auto-calculated fields
    subscription_start = models.DateField(editable=False)
    subscription_end = models.DateField(editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
        verbose_name = "دفعة اشتراك جمعية"
        verbose_name_plural = "دفعات اشتراكات الجمعيات"
    
    def save(self, *args, **kwargs):
        """
        Automatically calculate subscription dates and update organization
        """
        # Calculate subscription start date
        if not self.subscription_start:
            # Start from current end date or today (whichever is later)
            if self.organization.subscription_end_date:
                # If subscription hasn't expired yet, extend from end date
                today = timezone.now().date()
                if self.organization.subscription_end_date >= today:
                    self.subscription_start = self.organization.subscription_end_date + timedelta(days=1)
                else:
                    # Expired, start from today
                    self.subscription_start = today
            else:
                # No previous subscription, start from today
                self.subscription_start = timezone.now().date()
        
        # Calculate end date based on duration
        self.subscription_end = self.subscription_start + relativedelta(months=self.duration_months) - timedelta(days=1)
        
        # Save payment first
        super().save(*args, **kwargs)
        
        # Update organization subscription dates and status
        self.organization.subscription_start_date = self.subscription_start
        self.organization.subscription_end_date = self.subscription_end
        self.organization.subscription_status = 'active'  # Set status to active when payment is processed
        self.organization.is_active = True
        self.organization.save()
    
    def __str__(self):
        return f"{self.organization.name} - {self.payment_date} - {self.amount} ريال ({self.duration_months} شهر)"



class Staff(models.Model):
    """Staff members belong to an organization"""
    organization = models.ForeignKey(
        OrganizationInfo,
        on_delete=models.CASCADE,
        related_name='staff_members',
        verbose_name='الجمعية'
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='المستخدم')
    role = models.CharField(max_length=100, verbose_name='الدور')
    is_admin = models.BooleanField(default=False, verbose_name='مدير')
    started = models.DateField(default=timezone.now, verbose_name='تاريخ البدء')
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='الراتب')
    datepay = models.DateField(default=timezone.now, verbose_name='تاريخ الدفع')
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني')
    phone_number = models.CharField(max_length=15, blank=True, verbose_name='رقم الهاتف')

    class Meta:
        verbose_name = 'موظف'
        verbose_name_plural = 'الموظفون'

    def __str__(self):
        return f"{self.user.username} - {self.organization.name}"


def image_upload_to(instance, filename):
    """Upload to organization-specific directory"""
    ext = filename.split('.')[-1]
    filename = f"{instance.first_name}_{instance.last_name}.{ext}".lower()
    return os.path.join(
        f"organizations/{instance.organization.slug}/trainees/{now().year}/{now().month:02}/",
        filename
    )


class Trainer(models.Model):
    """Trainers belong to an organization"""
    organization = models.ForeignKey(
        OrganizationInfo,
        on_delete=models.CASCADE,
        related_name='trainers',
        verbose_name='الجمعية'
    )
    
    belts = (
        ("أبيض", "أبيض"),
        ("برتقالي", "برتقالي"),
        ("أصفر", "أصفر"),
        ("أصفر مع شريط أخضر", "أصفر مع شريط أخضر"),
        ("أخضر", "أخضر"),
        ("أخضر مع شريط أزرق", "أخضر مع شريط أزرق"),
        ("أزرق", "أزرق"),
        ("أزرق مع شريط أحمر", "أزرق مع شريط أحمر"),
        ("أحمر", "أحمر"),
        ("أحمر مع شريط أسود", "أحمر مع شريط أسود"),
        ("أسود", "أسود"),
    )

    CatChoices = (
        ("الصغار", "الصغار"),
        ("فتيان", "فتيان"),
        ("كبار", "كبار"),
        ('نساء', 'نساء'),
        ("شبان", "شبان"),
    )
    
    first_name = models.CharField(max_length=255, verbose_name='الاسم الأول')
    last_name = models.CharField(max_length=255, verbose_name='اسم العائلة')
    birth_day = models.DateField(verbose_name='تاريخ الميلاد')
    phone = models.CharField(max_length=15, blank=True, verbose_name='الهاتف')
    phone_parent = models.CharField(max_length=15, blank=True, verbose_name='هاتف ولي الأمر')
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني')
    CIN = models.CharField(max_length=30, blank=True, verbose_name='رقم البطاقة')
    address = models.CharField(max_length=50, blank=True, verbose_name='العنوان')
    male_female = models.CharField(
        max_length=11,
        choices=(('male', 'ذكر'), ('female', 'أنثى')),
        verbose_name='الجنس'
    )
    belt_degree = models.CharField(max_length=50, choices=belts, null=True, blank=True, verbose_name='درجة الحزام')
    Degree = models.CharField(max_length=80, null=True, blank=True, verbose_name='المستوى التعليمي')
    category = models.CharField(max_length=9, choices=CatChoices, default="small", verbose_name='الفئة')
    tall = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='الطول')
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='الوزن')
    started_day = models.DateField(default=timezone.now, verbose_name='تاريخ البدء')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    image = models.ImageField(
        upload_to=image_upload_to,
        blank=True,
        verbose_name='الصورة',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
        )   

    class Meta:
        verbose_name = 'متدرب'
        verbose_name_plural = 'المتدربون'
        ordering = ['-started_day']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['first_name', 'last_name']),
        
        ]

    @property
    def age(self):
        if self.birth_day:
            today = now().date()
            age = today.year - self.birth_day.year
            if (today.month, today.day) < (self.birth_day.month, self.birth_day.day):
                age -= 1
            return age
        return None

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name

    @staticmethod
    def get_belt_choices():
        return Trainer.belts
def document_upload_to(instance, filename):
    return (
        f"organizations/{instance.trainer.organization.slug}/"
        f"trainees/documents/{instance.trainer.id}/{filename}"
    )
def validate_file_size(value):
    max_size = 5 * 1024 * 1024  # 5MB
    if value.size > max_size:
        raise ValidationError("الملف كبير جداً (الحد الأقصى 5MB)")
class TrainerDocument(models.Model):
    DOC_TYPES = (
        ('بطاقة الوطنية', 'بطاقة الوطنية'),
        ('الحالة المدنية', 'الحالة المدنية'),
        ('وثيقة أخرى', 'وثيقة أخرى'),
    )
    
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='المتدرب'
    )
    document_type = models.CharField(
        max_length=20,
        choices=DOC_TYPES,
        verbose_name='نوع الوثيقة'
    )
    file = models.FileField(
    upload_to=document_upload_to,
    validators=[validate_file_size],
    verbose_name='الملف'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الرفع'
    )
    
    class Meta:
        verbose_name = 'وثيقة متدرب'
        verbose_name_plural = 'وثائق المتدربين'
        unique_together = ['trainer', 'document_type']

class Payments(models.Model):
    """Payment records scoped to organization"""
    organization = models.ForeignKey(
        OrganizationInfo,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='الجمعية'
    )
    
    CatChoices = (
        ("month", "شهرية"),
        ("subscription", "انخراط"),
        ("assurance", "التأمين"),
        ("jawaz", "جواز"),
    )
    
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='payments', verbose_name='المتدرب')
    paymentdate = models.DateField(default=timezone.now, verbose_name='تاريخ الدفع')
    paymentCategry = models.CharField(choices=CatChoices, max_length=20, verbose_name='نوع الدفع')
    paymentAmount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    
    class Meta:
        
        verbose_name = 'دفعة'
        verbose_name_plural = 'الدفعات'
        ordering = ['-paymentdate']
        indexes = [
            models.Index(fields=['organization', 'paymentdate']),
            models.Index(fields=['trainer', 'paymentCategry']),
            
        ]

    def __str__(self):
        return f"{self.trainer.full_name} - {self.get_paymentCategry_display()}"
    
    @staticmethod
    def get_catchoices():
        return Payments.CatChoices


class Article(models.Model):
    """Events/Articles scoped to organization"""
    organization = models.ForeignKey(
        OrganizationInfo,
        on_delete=models.CASCADE,
        related_name='articles',
        verbose_name='الجمعية'
    )
    
    choices = (
        ('local', 'محلي'),
        ('reigion', 'جهوي'),
        ('national', 'وطني'),
    )
    
    cts = (
        ('League', 'بطولة'),
        ('training', 'تدريب'),
        ('dawri', 'دوري'),
        ('test', 'امتحان'),
        ('out', 'خرجة'),
        ('other', 'اخرى'),
    )
    
    date = models.DateField(default=timezone.now, verbose_name='التاريخ')
    title = models.CharField(max_length=200, verbose_name='العنوان')
    location = models.CharField(max_length=500, default="اركانة نجوم اركانة", verbose_name='المكان')
    content = RichTextField(verbose_name='المحتوى')
    trainees = models.ManyToManyField(Trainer, blank=True, related_name='articles', verbose_name='المتدربون')
    category = models.CharField(choices=cts, max_length=30, verbose_name='الفئة')
    area = models.CharField(choices=choices, max_length=30, verbose_name='النطاق')
    costs = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='التكاليف')
    participetion_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='سعر المشاركة')

    class Meta:
        verbose_name = 'مقال'
        verbose_name_plural = 'المقالات'
        ordering = ['-date']

    @property
    def profit(self):
        return self.participetion_price * self.trainees.count()

    @property
    def net_profit(self):
        return self.profit - self.costs

    def __str__(self):
        return self.title
    
    @staticmethod
    def get_area_choices():
        return Article.choices
    
    @staticmethod
    def get_categories():
        return Article.cts


class Costs(models.Model):
    """Expenses scoped to organization"""
    organization = models.ForeignKey(
        OrganizationInfo,
        on_delete=models.CASCADE,
        related_name='costs',
        verbose_name='الجمعية'
    )
    cost = models.CharField(max_length=100, verbose_name='المصروف')
    desc = models.TextField(blank=True, verbose_name='الوصف')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    date = models.DateTimeField(verbose_name='التاريخ')
    is_recurring = models.BooleanField(default=False, verbose_name='متكرر')

    class Meta:
        verbose_name = 'مصروف'
        verbose_name_plural = 'المصاريف'
        ordering = ['-date']

    def __str__(self):
        return self.cost


class Addedpay(models.Model):
    """Additional payments/income scoped to organization"""
    organization = models.ForeignKey(
        OrganizationInfo,
        on_delete=models.CASCADE,
        related_name='additional_payments',
        verbose_name='الجمعية'
    )
    title = models.CharField(max_length=100, verbose_name='العنوان')
    desc = models.TextField(blank=True, verbose_name='الوصف')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    date = models.DateTimeField(verbose_name='التاريخ')

    class Meta:
        verbose_name = 'دفعة إضافية'
        verbose_name_plural = 'الدفعات الإضافية'
        ordering = ['-date']

    def __str__(self):
        return self.title


class Emailed(models.Model):
    """Email log scoped to organization"""
    organization = models.ForeignKey(
        OrganizationInfo,
        on_delete=models.CASCADE,
        related_name='emails',
        verbose_name='الجمعية'
    )
    user = models.ForeignKey(Trainer, on_delete=models.CASCADE, verbose_name='المتدرب')
    datetime = models.DateTimeField(default=timezone.now, verbose_name='التاريخ والوقت')
    email = models.EmailField(verbose_name='البريد الإلكتروني')
    category = models.CharField(max_length=300, default='monthly', verbose_name='الفئة')
    sent_successfully = models.BooleanField(default=True, verbose_name='تم الإرسال بنجاح')

    class Meta:
        verbose_name = 'بريد إلكتروني'
        verbose_name_plural = 'البريد الإلكتروني'
        ordering = ['-datetime']

    def __str__(self):
        return f"{self.user.full_name} - {self.category}"
    


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver([post_save, post_delete], sender=Payments)
def invalidate_dashboard_cache(sender, instance, **kwargs):
    """Auto-clear cache when payments change"""
    today = timezone.now().date()
    org_id = instance.organization_id
    
    cache_keys = [
        f'financial_summary_{org_id}_{today}',
        f'chart_data_{org_id}_{today}',
    ]
    cache.delete_many(cache_keys)

@receiver([post_save, post_delete], sender=Payments)
def invalidate_financial_cache(sender, instance, **kwargs):
    """Clear financial report cache when payments change"""
    from django.core.cache import cache
    org_id = instance.organization_id
    
    # Clear all cached reports for this organization
    # Since we don't know all date ranges, we'd need a more sophisticated approach
    # For now, just clear dashboard caches
    today = timezone.now().date()
    cache_keys = [
        f'financial_summary_{org_id}_{today}',
        f'chart_data_{org_id}_{today}',
    ]
    cache.delete_many(cache_keys)

@receiver([post_save, post_delete], sender=Costs)
def invalidate_costs_cache(sender, instance, **kwargs):
    """Clear cache when costs change"""
    from django.core.cache import cache
    org_id = instance.organization_id
    today = timezone.now().date()
    cache_keys = [
        f'financial_summary_{org_id}_{today}',
    ]
    cache.delete_many(cache_keys)