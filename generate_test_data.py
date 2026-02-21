"""
Generate synthetic test data for training and testing the ML model.
This script creates realistic student records and test results.
"""
import sqlite3
import random
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
#  TEST DATA GENERATION
# ─────────────────────────────────────────────

def connect_db():
    """Connect to database"""
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def generate_students(count=20):
    """Generate synthetic student data"""
    first_names = ["Aarav", "Vivaan", "Arjun", "Rishi", "Rohan", "Anush", "Priya", "Diya", "Pooja", "Neha", 
                   "Aditya", "Karan", "Nikhil", "Sarthak", "Daksh", "Sakshi", "Isha", "Ananya", "Sneha", "Shreya"]
    last_names = ["Kumar", "Singh", "Patel", "Sharma", "Gupta", "Verma", "Reddy", "Nair", "Iyer", "Desai"]
    
    students = []
    for i in range(count):
        first = random.choice(first_names)
        last = random.choice(last_names)
        name = f"{first} {last}"
        email = f"student{i+1}@college.edu"
        password = "password123"
        dob = f"{random.randint(1998, 2005)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        
        students.append((name, email, password, dob))
    
    return students


def generate_test_results(student_count=20):
    """
    Generate diverse test results covering all 4 mental health categories:
    - Excellent (score 8-16)
    - Moderate (score 17-24)
    - High Stress (score 25-32)
    - Severe (score 33-40)
    """
    results = []
    
    # Category 1: EXCELLENT (20% of data)
    for student_id in range(1, max(2, int(student_count * 0.2)) + 1):
        for _ in range(random.randint(2, 3)):  # 2-3 tests per student
            result = {
                'student_id': student_id,
                'stress': random.randint(1, 2),
                'anxiety': random.randint(1, 2),
                'sleep': random.randint(4, 5),  # Good sleep (inverted)
                'focus': random.randint(1, 2),
                'social': random.randint(4, 5),  # Good social connection (inverted)
                'sadness': random.randint(1, 2),
                'energy': random.randint(4, 5),
                'overwhelm': random.randint(1, 2),
                'result': 'Excellent Mental Well-being'
            }
            results.append(result)
    
    # Category 2: MODERATE (35% of data)
    start_id = max(2, int(student_count * 0.2)) + 1
    end_id = start_id + int(student_count * 0.35)
    for student_id in range(start_id, end_id + 1):
        for _ in range(random.randint(2, 3)):
            result = {
                'student_id': student_id,
                'stress': random.randint(2, 4),
                'anxiety': random.randint(2, 4),
                'sleep': random.randint(2, 4),
                'focus': random.randint(2, 4),
                'social': random.randint(2, 4),
                'sadness': random.randint(2, 3),
                'energy': random.randint(2, 4),
                'overwhelm': random.randint(2, 4),
                'result': 'Moderate Stress Detected'
            }
            results.append(result)
    
    # Category 3: HIGH STRESS (30% of data)
    start_id = end_id + 1
    end_id = start_id + int(student_count * 0.30)
    for student_id in range(start_id, end_id + 1):
        for _ in range(random.randint(2, 3)):
            result = {
                'student_id': student_id,
                'stress': random.randint(3, 5),
                'anxiety': random.randint(4, 5),
                'sleep': random.randint(1, 3),
                'focus': random.randint(3, 5),
                'social': random.randint(1, 3),
                'sadness': random.randint(3, 5),
                'energy': random.randint(1, 3),
                'overwhelm': random.randint(4, 5),
                'result': 'High Stress & Anxiety'
            }
            results.append(result)
    
    # Category 4: SEVERE (15% of data)
    start_id = end_id + 1
    end_id = student_count
    for student_id in range(start_id, end_id + 1):
        for _ in range(random.randint(1, 2)):
            result = {
                'student_id': student_id,
                'stress': random.randint(4, 5),
                'anxiety': random.randint(4, 5),
                'sleep': random.randint(1, 2),
                'focus': random.randint(4, 5),
                'social': random.randint(1, 2),
                'sadness': random.randint(4, 5),
                'energy': random.randint(1, 2),
                'overwhelm': random.randint(4, 5),
                'result': 'Severe Distress Detected'
            }
            results.append(result)
    
    return results


def insert_data(students, results):
    """Insert generated data into database"""
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("📊 INSERTING TEST DATA")
    print("=" * 60)
    
    # Insert students
    for name, email, password, dob in students:
        try:
            cur.execute(
                "INSERT INTO students (name, email, password, dob) VALUES (?, ?, ?, ?)",
                (name, email, password, dob)
            )
        except sqlite3.IntegrityError:
            print(f"⚠️  Student {email} already exists, skipping...")
    
    conn.commit()
    print(f"✅ Inserted {len(students)} students")
    
    # Insert test results
    for result in results:
        try:
            cur.execute("""
                INSERT INTO test_results
                  (student_id, stress, anxiety, sleep, focus, social,
                   sadness, energy, overwhelm, total_score, result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result['student_id'],
                result['stress'],
                result['anxiety'],
                result['sleep'],
                result['focus'],
                result['social'],
                result['sadness'],
                result['energy'],
                result['overwhelm'],
                (result['stress'] + result['anxiety'] + (6 - result['sleep']) + 
                 result['focus'] + (6 - result['social']) + result['sadness'] + 
                 result['energy'] + result['overwhelm']),
                result['result']
            ))
        except sqlite3.IntegrityError as e:
            print(f"⚠️  Error inserting test result: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Inserted {len(results)} test results")
    
    # Print summary
    print_summary(results)


def print_summary(results):
    """Print summary of generated data"""
    print("\n" + "=" * 60)
    print("📈 DATA DISTRIBUTION SUMMARY")
    print("=" * 60)
    
    categories = {}
    for result in results:
        category = result['result']
        categories[category] = categories.get(category, 0) + 1
    
    total = len(results)
    for category, count in sorted(categories.items()):
        percentage = (count / total) * 100
        print(f"{category:.<40} {count:>3} ({percentage:>5.1f}%)")
    
    print("=" * 60)
    print(f"Total test results: {total}")
    print("=" * 60)


def clear_and_regenerate():
    """Clear existing data and regenerate"""
    conn = connect_db()
    cur = conn.cursor()
    
    print("\n" + "⚠️  CLEARING EXISTING DATA...")
    
    # Get current student count
    current_count = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    current_tests = cur.execute("SELECT COUNT(*) FROM test_results").fetchone()[0]
    
    if current_count > 0:
        cur.execute("DELETE FROM test_results")
        cur.execute("DELETE FROM students")
        conn.commit()
        print(f"✅ Deleted {current_tests} test results and {current_count} students")
    
    conn.close()


def main():
    """Main function"""
    print("\n🎯 TEST DATA GENERATOR FOR STUDENT MENTAL HEALTH ANALYZER")
    print("\nThis will generate synthetic student data for ML model testing.\n")
    
    # Ask user
    response = input("Clear existing data and regenerate? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("❌ Cancelled.")
        return
    
    clear_and_regenerate()
    
    # Generate data
    num_students = 30
    students = generate_students(num_students)
    results = generate_test_results(num_students)
    
    # Insert into database
    insert_data(students, results)
    
    print("\n" + "=" * 60)
    print("🚀 TEST DATA READY!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python train_model.py")
    print("2. This will train the Logistic Regression model")
    print("3. Model will be saved to models/logistic_model.pkl")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
