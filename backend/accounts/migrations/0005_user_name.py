# Generated for V-Match: 이름(name) 필드 추가

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_email_code_attempts_user_email_code_expires_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='name',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
