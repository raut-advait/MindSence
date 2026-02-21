#!/usr/bin/env python
"""Quick test of the external data loader"""

from load_external_data import MentalHealthDataLoader

print("\n" + "="*70)
print("📊 EXTERNAL DATA LOADER TEST")
print("="*70)

loader = MentalHealthDataLoader()
summary = loader.get_summary()

print(f"\n✅ Total Students in Database: {summary['total_students']}")
print(f"✅ Total Test Records: {summary['total_tests']}")

print("\n📈 Current Category Distribution:")
print("-" * 70)
for category, count in sorted(summary['categories'].items()):
    if summary['total_tests'] > 0:
        percentage = (count / summary['total_tests']) * 100
        bar = "█" * (count // 2) if count > 0 else ""
        print(f"{category:.<45} {count:>3} ({percentage:>5.1f}%) {bar}")
    else:
        print(f"{category:.<45} {count:>3}")

print("-" * 70)
print("\n✅ Data Loader is Ready!")
print("\nNext Steps:")
print("1. Download a dataset from Kaggle, OR")
print("2. Prepare your own CSV file, THEN")
print("3. Run: python load_external_data.py")
print("="*70 + "\n")
