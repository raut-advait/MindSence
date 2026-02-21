#!/usr/bin/env python3
"""
Test the complete quiz -> prediction -> scoring flow with Flask
"""

import requests
import json
from time import sleep

BASE_URL = "http://localhost:5000"

# Color-coded output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def test_case(name, responses):
    """Test a quiz submission with given responses"""
    print(f"\n{Colors.BLUE}Test Case: {Colors.BOLD}{name}{Colors.RESET}")
    print("-" * 80)
    
    data = {
        'stress': responses[0],
        'anxiety': responses[1],
        'sleep': responses[2],
        'focus': responses[3],
        'social': responses[4],
        'sadness': responses[5],
        'energy': responses[6],
        'overwhelm': responses[7]
    }
    
    print(f"Responses: Stress={data['stress']}, Anxiety={data['anxiety']}, Sleep={data['sleep']}, "
          f"Focus={data['focus']}, Social={data['social']}, Sadness={data['sadness']}, "
          f"Energy={data['energy']}, Overwhelm={data['overwhelm']}")
    
    try:
        # Submit the form
        response = requests.post(f"{BASE_URL}/predict", data=data)
        
        if response.status_code == 200:
            # Extract score from HTML response
            if "/40" in response.text:
                # Find the score in the response
                import re
                match = re.search(r'(\d+)/40', response.text)
                if match:
                    score = match.group(1)
                    print(f"{Colors.GREEN}✓ Score Received: {Colors.BOLD}{score}/40{Colors.RESET}")
                    
                    # Check for category
                    if "Excellent" in response.text:
                        print(f"  Category: {Colors.GREEN}Excellent Mental Well-being{Colors.RESET}")
                    elif "Moderate" in response.text:
                        print(f"  Category: {Colors.YELLOW}Moderate Stress Detected{Colors.RESET}")
                    elif "High" in response.text:
                        print(f"  Category: {Colors.YELLOW}High Stress & Anxiety{Colors.RESET}")
                    elif "Severe" in response.text:
                        print(f"  Category: {Colors.RED}Severe Distress Detected{Colors.RESET}")
                    
                    return int(score)
                else:
                    print(f"{Colors.RED}✗ Could not extract score from response{Colors.RESET}")
                    return None
            else:
                print(f"{Colors.RED}✗ No score format found in response{Colors.RESET}")
                return None
        else:
            print(f"{Colors.RED}✗ Request failed with status {response.status_code}{Colors.RESET}")
            return None
            
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
        return None

def main():
    print(f"\n{Colors.BOLD}{'='*80}")
    print("TESTING COMPLETE QUIZ -> PREDICTION -> SCORE FLOW")
    print("="*80 + f"{Colors.RESET}\n")
    
    # Give Flask time to start
    print("Waiting for Flask to respond...")
    for i in range(5):
        try:
            requests.get(f"{BASE_URL}/test", timeout=1)
            print(f"{Colors.GREEN}✓ Flask is responding{Colors.RESET}\n")
            break
        except:
            if i < 4:
                sleep(1)
            else:
                print(f"{Colors.RED}✗ Flask not responding after 5 seconds{Colors.RESET}")
                return
    
    results = []
    
    # Test Case 1: Perfect health (all 1s)
    score1 = test_case("Perfect Health (all 1s)", [1, 1, 1, 1, 1, 1, 1, 1])
    if score1 is not None:
        results.append(("Perfect Health", score1))
    
    # Test Case 2: Slightly elevated (all 2s)
    score2 = test_case("Slightly Elevated (all 2s)", [2, 2, 2, 2, 2, 2, 2, 2])
    if score2 is not None:
        results.append(("Slightly Elevated", score2))
    
    # Test Case 3: Moderate (all 3s)
    score3 = test_case("Moderate Stress (all 3s)", [3, 3, 3, 3, 3, 3, 3, 3])
    if score3 is not None:
        results.append(("Moderate Stress", score3))
    
    # Test Case 4: High stress (all 4s)
    score4 = test_case("High Stress (all 4s)", [4, 4, 4, 4, 4, 4, 4, 4])
    if score4 is not None:
        results.append(("High Stress", score4))
    
    # Test Case 5: Very high stress (all 5s)
    score5 = test_case("Very High Stress (all 5s)", [5, 5, 5, 5, 5, 5, 5, 5])
    if score5 is not None:
        results.append(("Very High Stress", score5))
    
    # Test Case 6: Mixed responses
    score6 = test_case("Mixed Responses (2,3,2,4,2,3,2,3)", [2, 3, 2, 4, 2, 3, 2, 3])
    if score6 is not None:
        results.append(("Mixed Responses", score6))
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*80}")
    print("SUMMARY")
    print("="*80 + f"{Colors.RESET}\n")
    
    if results:
        print(f"{Colors.BOLD}Score Distribution:{Colors.RESET}")
        for test_name, score in results:
            print(f"  {test_name:25} → {score:2}/40")
        
        min_score = min(r[1] for r in results)
        max_score = max(r[1] for r in results)
        avg_score = sum(r[1] for r in results) / len(results)
        
        print(f"\n{Colors.BOLD}Range:{Colors.RESET}")
        print(f"  Min: {min_score}/40, Max: {max_score}/40, Avg: {avg_score:.1f}/40")
        
        # Validate that scores aren't clustered at extremes
        if min_score > 0 and max_score < 40:
            print(f"\n{Colors.GREEN}✓ PASS: Scores are properly distributed (not at extremes 0 or 40){Colors.RESET}")
        elif min_score == 0 and max_score == 40:
            print(f"\n{Colors.RED}✗ FAIL: Scores clustered at extremes (0 and 40){Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}⚠ WARNING: Check score distribution{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ No results collected{Colors.RESET}")

if __name__ == "__main__":
    main()
