"""
Load and integrate external mental health datasets.
Supports multiple dataset formats and normalizes them for training.
"""
import pandas as pd
import sqlite3
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────
#  DATASET LOADER WITH MULTIPLE FORMATS SUPPORT
# ─────────────────────────────────────────────

class MentalHealthDataLoader:
    """Load and normalize different mental health datasets"""
    
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self.conn = None
    
    def connect_db(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        return self.conn
    
    def close_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    # ─────────────────────────────────────────────
    #  DATASET 1: KAGGLE STUDENT MENTAL HEALTH
    # ─────────────────────────────────────────────
    def load_kaggle_student_mental_health(self, csv_path):
        """
        Load Kaggle Student Mental Health dataset
        Expected columns: age, cgpa, anxiety, panic, depression
        Maps to our 8-factor model
        """
        print(f"\n📥 Loading Kaggle Student Mental Health Dataset: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            print(f"✅ Loaded {len(df)} records")
            
            # Map columns to our 8-factor model
            records = []
            for idx, row in df.iterrows():
                # Normalize anxiety and depression to 1-5 scale
                anxiety = self._normalize_to_scale(row.get('anxiety', 3), 1, 5)
                depression = self._normalize_to_scale(row.get('depression', 3), 1, 5)
                panic = self._normalize_to_scale(row.get('panic', 3), 1, 5)
                
                # Estimate CGPA impact on focus/stress
                cgpa = float(row.get('cgpa', 3.0)) if row.get('cgpa') else 3.0
                focus = self._normalize_to_scale(5 - cgpa, 1, 5)  # Lower CGPA = lower focus
                
                record = {
                    'stress': anxiety,  # anxiety as stress
                    'anxiety': anxiety,
                    'sleep': self._normalize_to_scale(row.get('sleep_quality', 3), 1, 5),
                    'focus': focus,
                    'social': self._normalize_to_scale(row.get('social_interaction', 3), 1, 5),
                    'sadness': depression,
                    'energy': self._normalize_to_scale(5 - depression, 1, 5),  # Depression inversely affects energy
                    'overwhelm': panic,
                    'result': self._categorize_mental_health(anxiety, depression, panic)
                }
                records.append(record)
            
            return records
        
        except Exception as e:
            print(f"❌ Error loading Kaggle dataset: {e}")
            return []
    
    # ─────────────────────────────────────────────
    #  DATASET 2: MENTAL HEALTH IN TECH SURVEY
    # ─────────────────────────────────────────────
    def load_mental_health_tech_survey(self, csv_path):
        """
        Load Mental Health in Tech Survey dataset
        Maps work stress, benefits, supervisor support to mental health factors
        """
        print(f"\n📥 Loading Mental Health in Tech Survey: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            print(f"✅ Loaded {len(df)} records")
            
            records = []
            for idx, row in df.iterrows():
                # Extract relevant features
                work_interference = 1  # Default
                if 'work_interfere' in df.columns:
                    val = str(row['work_interfere']).lower()
                    if 'often' in val or 'frequently' in val:
                        work_interference = 5
                    elif 'sometimes' in val or 'rarely' in val:
                        work_interference = 3
                
                seek_help = 1  # Default
                if 'seek_help' in df.columns:
                    val = str(row['seek_help']).lower()
                    if 'yes' in val:
                        seek_help = 2
                    else:
                        seek_help = 4
                
                record = {
                    'stress': work_interference,
                    'anxiety': self._normalize_to_scale(work_interference, 1, 5),
                    'sleep': 3,  # Neutral estimate
                    'focus': 4 - work_interference,  # Work interference affects focus
                    'social': self._normalize_to_scale(seek_help, 1, 5),
                    'sadness': 3,  # Neutral
                    'energy': 5 - work_interference,
                    'overwhelm': work_interference,
                    'result': self._categorize_by_work_stress(work_interference)
                }
                records.append(record)
            
            return records
        
        except Exception as e:
            print(f"❌ Error loading tech survey dataset: {e}")
            return []
    
    # ─────────────────────────────────────────────
    #  DATASET 3: CUSTOM CSV FORMAT
    # ─────────────────────────────────────────────
    def load_custom_csv(self, csv_path, column_mapping):
        """
        Load custom CSV with user-defined column mapping
        
        Args:
            csv_path: Path to CSV file
            column_mapping: Dict mapping CSV columns to our factors
                Example:
                {
                    'stress_level': 'stress',
                    'anxiety_score': 'anxiety',
                    'sleep_hours': 'sleep',
                    ...
                }
        """
        print(f"\n📥 Loading Custom CSV: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            print(f"✅ Loaded {len(df)} records")
            
            records = []
            for idx, row in df.iterrows():
                record = {}
                for csv_col, factor_col in column_mapping.items():
                    if csv_col in df.columns:
                        value = row[csv_col]
                        # Normalize to 1-5 scale if needed
                        if isinstance(value, (int, float)):
                            record[factor_col] = self._normalize_to_scale(value, 1, 5)
                        else:
                            record[factor_col] = 3  # Default
                
                # Ensure all 8 factors exist
                factors = ['stress', 'anxiety', 'sleep', 'focus', 'social', 'sadness', 'energy', 'overwhelm']
                for factor in factors:
                    if factor not in record:
                        record[factor] = 3
                
                # Add result category
                total = sum([record[f] for f in factors])
                record['result'] = self._categorize_by_score(total)
                
                records.append(record)
            
            return records
        
        except Exception as e:
            print(f"❌ Error loading custom CSV: {e}")
            return []
    
    # ─────────────────────────────────────────────
    #  HELPER FUNCTIONS
    # ─────────────────────────────────────────────
    
    def _normalize_to_scale(self, value, min_val=1, max_val=5):
        """Normalize any value to 1-5 scale"""
        if isinstance(value, str):
            if any(x in value.lower() for x in ['high', 'severe', 'yes', 'often']):
                return max_val
            elif any(x in value.lower() for x in ['medium', 'moderate', 'sometimes']):
                return (min_val + max_val) // 2
            else:
                return min_val
        
        try:
            val = float(value)
            # Clamp to 1-5 range
            return max(min_val, min(max_val, int(val)))
        except:
            return 3  # Default middle value
    
    def _categorize_mental_health(self, anxiety, depression, panic):
        """Categorize based on mental health scores"""
        avg_score = (anxiety + depression + panic) / 3
        
        if avg_score <= 1.5:
            return "Excellent Mental Well-being"
        elif avg_score <= 2.5:
            return "Moderate Stress Detected"
        elif avg_score <= 4.0:
            return "High Stress & Anxiety"
        else:
            return "Severe Distress Detected"
    
    def _categorize_by_work_stress(self, stress_level):
        """Categorize based on work stress"""
        if stress_level <= 2:
            return "Excellent Mental Well-being"
        elif stress_level <= 3:
            return "Moderate Stress Detected"
        elif stress_level <= 4:
            return "High Stress & Anxiety"
        else:
            return "Severe Distress Detected"
    
    def _categorize_by_score(self, total_score):
        """Categorize based on total score"""
        if total_score <= 16:
            return "Excellent Mental Well-being"
        elif total_score <= 24:
            return "Moderate Stress Detected"
        elif total_score <= 32:
            return "High Stress & Anxiety"
        else:
            return "Severe Distress Detected"
    
    # ─────────────────────────────────────────────
    #  INSERT INTO DATABASE
    # ─────────────────────────────────────────────
    
    def insert_records(self, records, dataset_name="External Dataset"):
        """Insert loaded records into database"""
        self.connect_db()
        cur = self.conn.cursor()
        
        print(f"\n📊 Inserting {len(records)} records from {dataset_name}...")
        
        inserted = 0
        for record in records:
            try:
                # Calculate total score
                total_score = (
                    record['stress'] + record['anxiety'] + 
                    (6 - record['sleep']) + record['focus'] +
                    (6 - record['social']) + record['sadness'] +
                    record['energy'] + record['overwhelm']
                )
                
                # Create a dummy student if needed
                dummy_email = f"external_{inserted}@dataset.org"
                
                try:
                    cur.execute(
                        "INSERT INTO students (name, email, password, dob) VALUES (?, ?, ?, ?)",
                        (f"Dataset User {inserted}", dummy_email, "dataset", "2000-01-01")
                    )
                    self.conn.commit()
                except sqlite3.IntegrityError:
                    pass  # Student already exists
                
                # Get student ID
                student = cur.execute(
                    "SELECT id FROM students WHERE email = ?",
                    (dummy_email,)
                ).fetchone()
                
                if student:
                    student_id = student[0]
                    cur.execute("""
                        INSERT INTO test_results
                          (student_id, stress, anxiety, sleep, focus, social,
                           sadness, energy, overwhelm, total_score, result)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        student_id,
                        record['stress'],
                        record['anxiety'],
                        record['sleep'],
                        record['focus'],
                        record['social'],
                        record['sadness'],
                        record['energy'],
                        record['overwhelm'],
                        total_score,
                        record['result']
                    ))
                    inserted += 1
            
            except Exception as e:
                print(f"⚠️  Error inserting record: {e}")
        
        self.conn.commit()
        self.close_db()
        
        print(f"✅ Successfully inserted {inserted} records")
        return inserted
    
    def get_summary(self):
        """Get summary of data in database"""
        self.connect_db()
        cur = self.conn.cursor()
        
        total_students = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        total_tests = cur.execute("SELECT COUNT(*) FROM test_results").fetchone()[0]
        
        # Category breakdown
        categories = {}
        for row in cur.execute("SELECT result, COUNT(*) FROM test_results GROUP BY result").fetchall():
            categories[row[0]] = row[1]
        
        self.close_db()
        
        return {
            'total_students': total_students,
            'total_tests': total_tests,
            'categories': categories
        }


# ─────────────────────────────────────────────
#  EXAMPLE USAGE
# ─────────────────────────────────────────────

def main():
    loader = MentalHealthDataLoader()
    
    print("\n" + "=" * 70)
    print("🔄 EXTERNAL DATASET LOADER")
    print("=" * 70)
    
    print("\nAvailable options:")
    print("1. Load Kaggle Student Mental Health CSV")
    print("2. Load Mental Health in Tech Survey CSV")
    print("3. Load Custom CSV with column mapping")
    print("4. View current database summary")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '1':
        csv_path = input("Enter path to Kaggle CSV (e.g., student_mental_health.csv): ").strip()
        if Path(csv_path).exists():
            records = loader.load_kaggle_student_mental_health(csv_path)
            if records:
                loader.insert_records(records, "Kaggle Student Mental Health")
        else:
            print(f"❌ File not found: {csv_path}")
    
    elif choice == '2':
        csv_path = input("Enter path to Tech Survey CSV (e.g., mental_health_tech.csv): ").strip()
        if Path(csv_path).exists():
            records = loader.load_mental_health_tech_survey(csv_path)
            if records:
                loader.insert_records(records, "Mental Health in Tech Survey")
        else:
            print(f"❌ File not found: {csv_path}")
    
    elif choice == '3':
        csv_path = input("Enter path to Custom CSV: ").strip()
        if Path(csv_path).exists():
            print("\nEnter column mapping (CSV column -> our factor)")
            print("Factors: stress, anxiety, sleep, focus, social, sadness, energy, overwhelm")
            
            mapping = {}
            while True:
                csv_col = input("CSV column name (or 'done'): ").strip()
                if csv_col.lower() == 'done':
                    break
                factor = input(f"  Map to factor: ").strip()
                mapping[csv_col] = factor
            
            if mapping:
                records = loader.load_custom_csv(csv_path, mapping)
                if records:
                    loader.insert_records(records, f"Custom Dataset ({csv_path})")
        else:
            print(f"❌ File not found: {csv_path}")
    
    elif choice == '4':
        summary = loader.get_summary()
        print("\n" + "=" * 70)
        print("📈 DATABASE SUMMARY")
        print("=" * 70)
        print(f"Total Students: {summary['total_students']}")
        print(f"Total Tests: {summary['total_tests']}")
        print("\nCategory Distribution:")
        for category, count in summary['categories'].items():
            pct = (count / summary['total_tests'] * 100) if summary['total_tests'] > 0 else 0
            print(f"  {category:.<45} {count:>3} ({pct:>5.1f}%)")
        print("=" * 70)
    
    else:
        print("❌ Invalid option")

if __name__ == '__main__':
    main()
