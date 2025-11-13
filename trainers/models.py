from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField
from django.utils.timezone import now
from django.utils.text import slugify
import os


class OrganizationInfo(models.Model):
    """Main organization/tenant model"""
    name = models.CharField(max_length=255, verbose_name='اسم الجمعية')
    slug = models.SlugField(unique=True, verbose_name='المعرف')
    description = models.TextField(blank=True, verbose_name='الوصف')
    established_date = models.DateField(blank=True, null=True, verbose_name='تاريخ التأسيس')
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='مبلغ الإيجار')
    phone_number = models.CharField(max_length=15, blank=True, verbose_name='رقم الهاتف')
    email = models.EmailField(blank=True, verbose_name='البريد الإلكتروني')
    datepay = models.DateField(blank=True, null=True, verbose_name='تاريخ الدفع')
    
    # Subscription fields
    is_active = models.BooleanField(default=True, verbose_name='نشطة')
    subscription_tier = models.CharField(
        max_length=20,
        choices=[('free', 'مجاني'), ('basic', 'أساسي'), ('premium', 'متميز')],
        default='free',
        verbose_name='نوع الاشتراك'
    )
    max_trainers = models.IntegerField(default=50, verbose_name='الحد الأقصى للمتدربين')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'جمعية'
        verbose_name_plural = 'الجمعيات'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


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
    image = models.ImageField(upload_to=image_upload_to, blank=True, verbose_name='الصورة')

    class Meta:
        verbose_name = 'متدرب'
        verbose_name_plural = 'المتدربون'
        ordering = ['-started_day']
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['organization', 'category']),
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