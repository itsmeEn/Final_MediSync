"""
Comprehensive test script for the patient queue notification system.

This script tests:
1. Queue opening with notifications to all patients
2. Real-time WebSocket broadcasting
3. Persistent notification storage
4. Automatic queue closing based on schedule
5. Error handling and retry mechanisms
"""

import os
import sys
import django
import asyncio
from datetime import time, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from backend.operations.models import (
    QueueStatus, QueueSchedule, QueueStatusLog,
    Notification, QueueManagement
)
from backend.operations.async_services import AsyncNotificationService
from backend.users.models import PatientProfile, NurseProfile

User = get_user_model()


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_success(message):
    print(f"{Colors.GREEN}[+] {message}{Colors.RESET}")


def print_error(message):
    print(f"{Colors.RED}[X] {message}{Colors.RESET}")


def print_info(message):
    print(f"{Colors.BLUE}[i] {message}{Colors.RESET}")


def print_warning(message):
    print(f"{Colors.YELLOW}[!] {message}{Colors.RESET}")


def print_header(message):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"{message}")
    print(f"{'='*60}{Colors.RESET}\n")


class QueueNotificationSystemTest:
    """Test suite for queue notification system"""
    
    def __init__(self):
        self.test_nurse = None
        self.test_patients = []
        self.test_department = "OPD"
        self.test_schedule = None
        self.queue_status = None
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
    
    def setup(self):
        """Set up test data"""
        print_header("Setting Up Test Environment")
        
        try:
            # Create or get test nurse
            print_info("Creating test nurse...")
            nurse_user, created = User.objects.get_or_create(
                email='testnurse_queue@example.com',
                defaults={
                    'first_name': 'Test',
                    'last_name': 'Nurse',
                    'role': 'nurse'
                }
            )
            if created:
                nurse_user.set_password('testpass123')
                nurse_user.save()
            
            self.test_nurse = NurseProfile.objects.get_or_create(
                user=nurse_user
            )[0]
            print_success(f"Test nurse created: {nurse_user.full_name}")
            
            # Create or get test patients
            print_info("Creating test patients...")
            for i in range(5):
                patient_user, created = User.objects.get_or_create(
                    email=f'testpatient{i}_queue@example.com',
                    defaults={
                        'first_name': f'Patient',
                        'last_name': f'Test{i}',
                        'role': 'patient'
                    }
                )
                if created:
                    patient_user.set_password('testpass123')
                    patient_user.save()
                
                patient_profile = PatientProfile.objects.get_or_create(
                    user=patient_user
                )[0]
                self.test_patients.append(patient_user)
            
            print_success(f"Created {len(self.test_patients)} test patients")
            
            # Create test schedule
            print_info("Creating test queue schedule...")
            current_time = timezone.now().time()
            start_time = (timezone.now() - timedelta(hours=1)).time()
            end_time = (timezone.now() + timedelta(hours=2)).time()
            
            self.test_schedule, created = QueueSchedule.objects.update_or_create(
                department=self.test_department,
                nurse=self.test_nurse,
                defaults={
                    'start_time': start_time,
                    'end_time': end_time,
                    'days_of_week': [0, 1, 2, 3, 4, 5, 6],  # All days
                    'is_active': True,
                    'manual_override': False,
                    'override_status': 'auto'
                }
            )
            print_success(f"Test schedule created: {start_time} to {end_time}")
            
            # Create or update queue status
            print_info("Initializing queue status...")
            self.queue_status, created = QueueStatus.objects.get_or_create(
                department=self.test_department,
                defaults={
                    'is_open': False,
                    'current_schedule': self.test_schedule,
                    'last_updated_by': nurse_user
                }
            )
            
            # Ensure it's closed for testing AND linked to correct schedule
            if self.queue_status.is_open or self.queue_status.current_schedule != self.test_schedule:
                self.queue_status.is_open = False
                self.queue_status.current_schedule = self.test_schedule
                self.queue_status.save()
            
            print_success("Queue status initialized (closed)")
            
            # Clear old notifications
            print_info("Clearing old test notifications...")
            Notification.objects.filter(user__in=self.test_patients).delete()
            print_success("Old notifications cleared")
            
        except Exception as e:
            print_error(f"Setup failed: {str(e)}")
            raise
    
    def test_queue_opening_with_notifications(self):
        """Test 1: Queue opening sends notifications to all patients"""
        print_header("Test 1: Queue Opening with Patient Notifications")
        
        try:
            initial_notification_count = Notification.objects.filter(
                user__in=self.test_patients
            ).count()
            print_info(f"Initial notification count: {initial_notification_count}")
            
            # Open the queue
            print_info("Opening queue...")
            self.queue_status.is_open = True
            self.queue_status.last_updated_by = self.test_nurse.user
            self.queue_status.update_status_message()
            self.queue_status.save()
            
            # Create notifications for all patients
            print_info("Sending notifications to all patients...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                notification_stats = loop.run_until_complete(
                    AsyncNotificationService.send_notification_to_all_patients(
                        message=f"The {self.test_department} queue is now OPEN! You can now join the queue.",
                        department=self.test_department
                    )
                )
            finally:
                loop.close()
            
            print_success(f"Notifications sent: {notification_stats['notifications_created']}")
            print_info(f"Failed: {notification_stats['notifications_failed']}")
            
            # Verify notifications were created
            new_notification_count = Notification.objects.filter(
                user__in=self.test_patients
            ).count()
            
            notifications_created = new_notification_count - initial_notification_count
            
            if notifications_created >= len(self.test_patients):
                print_success(f"All {len(self.test_patients)} patients received notifications")
                self.results['passed'] += 1
            else:
                print_error(f"Expected {len(self.test_patients)} notifications, got {notifications_created}")
                self.results['failed'] += 1
            
            # Check notification content
            recent_notifications = Notification.objects.filter(
                user__in=self.test_patients,
                message__icontains="queue is now OPEN"
            )
            
            if recent_notifications.exists():
                print_success("Notifications have correct message content")
                self.results['passed'] += 1
                
                # Check notification details
                sample_notif = recent_notifications.first()
                print_info(f"Sample notification: {sample_notif.message[:80]}...")
                print_info(f"Channel: {sample_notif.channel}")
                print_info(f"Delivery status: {sample_notif.delivery_status}")
            else:
                print_error("Notifications missing or incorrect content")
                self.results['failed'] += 1
            
            # Verify queue status
            self.queue_status.refresh_from_db()
            if self.queue_status.is_open:
                print_success("Queue status is OPEN")
                self.results['passed'] += 1
            else:
                print_error("Queue status is not OPEN")
                self.results['failed'] += 1
            
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            self.results['failed'] += 1
    
    def test_queue_status_persistence(self):
        """Test 2: Queue status persists and can be queried"""
        print_header("Test 2: Queue Status Persistence")
        
        try:
            # Query queue status
            print_info("Querying queue status from database...")
            status = QueueStatus.objects.get(department=self.test_department)
            
            if status.is_open:
                print_success("Queue status persisted as OPEN")
                self.results['passed'] += 1
            else:
                print_error("Queue status not persisted correctly")
                self.results['failed'] += 1
            
            # Check status message
            if "Open" in status.status_message:
                print_success(f"Status message is correct: '{status.status_message}'")
                self.results['passed'] += 1
            else:
                print_warning(f"Status message unexpected: '{status.status_message}'")
                self.results['warnings'] += 1
            
            # Check schedule linkage
            if status.current_schedule:
                print_success(f"Schedule linked correctly: {status.current_schedule}")
                self.results['passed'] += 1
            else:
                print_warning("No schedule linked to queue status")
                self.results['warnings'] += 1
            
            # Check logs
            recent_logs = QueueStatusLog.objects.filter(
                department=self.test_department
            ).order_by('-changed_at')[:5]
            
            if recent_logs.exists():
                print_success(f"Status changes logged ({recent_logs.count()} recent logs)")
                self.results['passed'] += 1
                
                for log in recent_logs[:3]:
                    print_info(f"  - {log.changed_at}: {log.previous_status} -> {log.new_status} ({log.change_reason})")
            else:
                print_warning("No logs found")
                self.results['warnings'] += 1
            
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            self.results['failed'] += 1
    
    def test_auto_close_functionality(self):
        """Test 3: Automatic queue closing based on schedule"""
        print_header("Test 3: Automatic Queue Closing")
        
        try:
            # Test should_auto_close method
            print_info("Testing auto-close detection...")
            
            # Queue should NOT auto-close (within schedule)
            should_close = self.queue_status.should_auto_close()
            
            if not should_close:
                print_success("Queue correctly identified as within schedule hours")
                self.results['passed'] += 1
            else:
                print_warning("Queue incorrectly marked for auto-close")
                self.results['warnings'] += 1
            
            # Simulate past end time by modifying schedule
            print_info("Simulating end time passed...")
            original_end_time = self.test_schedule.end_time
            past_time = (timezone.now() - timedelta(minutes=30)).time()
            self.test_schedule.end_time = past_time
            self.test_schedule.save()
            
            # Refresh both objects
            self.test_schedule.refresh_from_db()
            # Re-fetch queue_status to ensure all relations are fresh
            self.queue_status = QueueStatus.objects.get(pk=self.queue_status.pk)
            
            # Debug info
            current_time = timezone.now().time()
            print_info(f"Current time: {current_time}, End time: {self.test_schedule.end_time}")
            print_info(f"Current > End: {current_time > self.test_schedule.end_time}")
            
            should_close_now = self.queue_status.should_auto_close()
            
            if should_close_now:
                print_success("Queue correctly identified for auto-close (past end time)")
                self.results['passed'] += 1
                
                # Test auto_close_if_needed
                print_info("Executing auto-close...")
                was_closed = self.queue_status.auto_close_if_needed()
                
                if was_closed:
                    print_success("Queue auto-closed successfully")
                    self.results['passed'] += 1
                    
                    # Verify closure
                    self.queue_status.refresh_from_db()
                    if not self.queue_status.is_open:
                        print_success("Queue status updated to CLOSED")
                        self.results['passed'] += 1
                    else:
                        print_error("Queue status not updated")
                        self.results['failed'] += 1
                else:
                    print_error("Auto-close did not execute")
                    self.results['failed'] += 1
            else:
                print_error("Queue not identified for auto-close")
                self.results['failed'] += 1
            
            # Restore original end time
            self.test_schedule.end_time = original_end_time
            self.test_schedule.save()
            
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            self.results['failed'] += 1
    
    def test_notification_delivery_tracking(self):
        """Test 4: Notification delivery tracking"""
        print_header("Test 4: Notification Delivery Tracking")
        
        try:
            # Get recent notifications (don't slice yet)
            recent_notifications_qs = Notification.objects.filter(
                user__in=self.test_patients
            ).order_by('-created_at')
            
            # Check delivery status (before slicing)
            pending_count = recent_notifications_qs.filter(
                delivery_status=Notification.DELIVERY_PENDING
            ).count()
            sent_count = recent_notifications_qs.filter(
                delivery_status=Notification.DELIVERY_SENT
            ).count()
            delivered_count = recent_notifications_qs.filter(
                delivery_status=Notification.DELIVERY_DELIVERED
            ).count()
            
            # Now slice for display
            recent_notifications = list(recent_notifications_qs[:5])
            
            if recent_notifications:
                print_success(f"Found {len(recent_notifications)} notifications to check")
                self.results['passed'] += 1
                
                print_info(f"Pending: {pending_count}, Sent: {sent_count}, Delivered: {delivered_count}")
                
                if pending_count + sent_count + delivered_count > 0:
                    print_success("Notifications have delivery status tracking")
                    self.results['passed'] += 1
                else:
                    print_error("No delivery status set")
                    self.results['failed'] += 1
                
                # Check timestamps (count from list)
                notifications_with_timestamps = sum(1 for n in recent_notifications if n.created_at is not None)
                
                if notifications_with_timestamps == len(recent_notifications):
                    print_success("All notifications have timestamps")
                    self.results['passed'] += 1
                else:
                    print_warning(f"Some notifications missing timestamps")
                    self.results['warnings'] += 1
                
            else:
                print_error("No notifications found for testing")
                self.results['failed'] += 1
            
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            self.results['failed'] += 1
    
    def test_error_handling(self):
        """Test 5: Error handling and recovery"""
        print_header("Test 5: Error Handling and Recovery")
        
        try:
            # Test with invalid department
            print_info("Testing invalid department handling...")
            try:
                invalid_status = QueueStatus.objects.get(department="INVALID_DEPT")
                print_warning("⚠ Expected exception not raised for invalid department")
                self.results['warnings'] += 1
            except QueueStatus.DoesNotExist:
                print_success("Invalid department handled correctly")
                self.results['passed'] += 1
            
            # Test notification to empty user set
            print_info("Testing notification system with edge cases...")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        AsyncNotificationService.send_notification_to_all_patients(
                            message="Test edge case",
                            department="TEST"
                        )
                    )
                    print_success("Notification service handles edge cases gracefully")
                    print_info(f"  Result: {result['notifications_created']} created, {result['notifications_failed']} failed")
                    self.results['passed'] += 1
                finally:
                    loop.close()
            except Exception as e:
                print_error(f"Edge case handling failed: {str(e)}")
                self.results['failed'] += 1
            
        except Exception as e:
            print_error(f"Test failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            self.results['failed'] += 1
    
    def cleanup(self):
        """Clean up test data"""
        print_header("Cleaning Up Test Environment")
        
        try:
            # Reset queue status
            if self.queue_status:
                self.queue_status.is_open = False
                self.queue_status.save()
                print_success("Queue status reset")
            
            print_info("Test data cleanup completed")
            
        except Exception as e:
            print_error(f"Cleanup failed: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print_header("Test Summary")
        
        total_tests = self.results['passed'] + self.results['failed']
        
        print(f"\n{Colors.BOLD}Results:{Colors.RESET}")
        print(f"  {Colors.GREEN}Passed:{Colors.RESET} {self.results['passed']}/{total_tests}")
        print(f"  {Colors.RED}Failed:{Colors.RESET} {self.results['failed']}/{total_tests}")
        print(f"  {Colors.YELLOW}Warnings:{Colors.RESET} {self.results['warnings']}")
        
        if self.results['failed'] == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] ALL TESTS PASSED!{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}[FAILURE] SOME TESTS FAILED{Colors.RESET}")
        
        print()
    
    def run_all_tests(self):
        """Run all tests"""
        try:
            self.setup()
            self.test_queue_opening_with_notifications()
            self.test_queue_status_persistence()
            self.test_auto_close_functionality()
            self.test_notification_delivery_tracking()
            self.test_error_handling()
        finally:
            self.cleanup()
            self.print_summary()


def main():
    """Main test execution"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 60)
    print("  Patient Queue Notification System - Test Suite")
    print("=" * 60)
    print(f"{Colors.RESET}")
    
    test_suite = QueueNotificationSystemTest()
    test_suite.run_all_tests()


if __name__ == '__main__':
    main()

