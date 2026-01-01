# Daily Interest Processing - Cron Job Setup

## Overview

This document explains how to set up the daily cron job to automatically process:
1. **Matured Investment Interest** - Adds interest to user savings when investments mature
2. **Uninvested Savings Interest** - Adds 15% interest on Dec 31, 2025
3. **Challenge Transfer** - Transfers all 52WSC 2025 savings to accounts on Jan 1, 2026

## Management Command

The command is located at:
```
savings_52_weeks/management/commands/process_daily_interest.py
```

### Usage

**Test run (dry-run mode):**
```bash
python manage.py process_daily_interest --dry-run
```

**Actual run:**
```bash
python manage.py process_daily_interest
```

## Setting Up Cron Job

### Option 1: Linux/Unix Cron

Add to crontab (runs daily at 2:00 AM):
```bash
crontab -e
```

Add this line:
```
0 2 * * * cd /path/to/your/project && /path/to/venv/bin/python manage.py process_daily_interest >> /path/to/logs/interest_processing.log 2>&1
```

### Option 2: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 2:00 AM
4. Action: Start a program
5. Program: `C:\path\to\venv\Scripts\python.exe`
6. Arguments: `manage.py process_daily_interest`
7. Start in: `D:\BACK UP 1\Mushana\Dash boards\mcs`

### Option 3: Using Django-Q or Celery (Recommended for Production)

If you're using Django-Q or Celery, you can schedule it as a periodic task:

**Django-Q example:**
```python
# In your settings.py or management command
from django_q.tasks import schedule

schedule(
    'savings_52_weeks.management.commands.process_daily_interest',
    name='Process Daily Interest',
    schedule_type='D',  # Daily
    repeats=-1,  # Forever
    next_run=datetime.now().replace(hour=2, minute=0)
)
```

## What Gets Processed

### 1. Matured Investments (Daily)
- Finds all investments with `status='matured'` and `interest_paid=False`
- Calculates total interest expected
- Creates a deposit transaction for the interest amount
- Marks investment as `interest_paid=True`
- Transaction receipt format: `INT-{investment_id}-{date}`

### 2. Uninvested Savings Interest (Dec 31, 2025 only)
- Runs only on December 31, 2025
- For each user with 52WSC project:
  - Calculates uninvested savings (total savings - invested amount)
  - Calculates 15% interest on uninvested amount
  - Creates deposit transaction
  - Transaction receipt format: `UNINV-INT-2025-{user_id}`

### 3. Challenge Transfer (Jan 1, 2026 only)
- Runs only on January 1, 2026
- For each user with 52WSC project:
  - Calculates total savings (including all interest)
  - Creates transfer transaction
  - Transaction receipt format: `TRANSFER-2025-{user_id}-{date}`
  - **Note**: You may want to implement additional logic to archive 2025 data

## Logging

The command outputs detailed information:
- Number of investments processed
- Total interest paid
- Users processed
- Any errors encountered

For production, redirect output to a log file:
```bash
python manage.py process_daily_interest >> /var/log/52wsc_interest.log 2>&1
```

## Testing

Before setting up the cron job, test the command:

1. **Dry-run test:**
   ```bash
   python manage.py process_daily_interest --dry-run
   ```
   This shows what would be processed without making changes.

2. **Manual test:**
   ```bash
   python manage.py process_daily_interest
   ```
   This actually processes the transactions.

3. **Check results:**
   - View user dashboards to see new interest transactions
   - Check admin panel for updated investment statuses
   - Verify transaction history

## Important Dates

- **December 31, 2025**: Uninvested savings interest (15%) is added
- **January 1, 2026**: All 52WSC 2025 savings are transferred to accounts

## Troubleshooting

### Command not found
- Ensure you're in the project directory
- Activate virtual environment
- Check Django is installed

### No transactions created
- Check that investments have actually matured
- Verify user profiles have the 52WSC project
- Check for existing transactions (prevents duplicates)

### Errors processing
- Check database connection
- Verify user profiles exist
- Check for data integrity issues
- Review error messages in output

## Monitoring

Set up monitoring to ensure the cron job runs:
- Check log files daily
- Set up email alerts for errors
- Monitor transaction counts
- Verify interest amounts are correct

## Security

- Run cron job as a non-privileged user
- Restrict file permissions on log files
- Use secure database connections
- Audit transaction logs regularly

## Next Steps

After setting up the cron job:
1. Test with --dry-run first
2. Run manually once to verify
3. Set up cron job
4. Monitor first few runs
5. Set up alerts for failures

---

**Last Updated**: December 2025  
**Command**: `process_daily_interest`  
**Frequency**: Daily at 2:00 AM (recommended)

