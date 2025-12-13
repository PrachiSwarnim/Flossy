from reminders import check_reminders_sync
print("Testing reminder check...")
try:
    check_reminders_sync()
    print("✅ Reminder check passed (DB schema is correct).")
except Exception as e:
    print(f"❌ Reminder check FAILED: {e}")
