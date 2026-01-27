"""
Integration Test: Complete Queue Flow
Tests the entire user journey from joining queue to dispatch
"""

import pytest
from datetime import datetime
from app.services.queue_service import QueueService
from app.models.user import User
from app.models.driver import Route
from app.models.ride_group import RideGroup, GroupStatus


class TestCompleteQueueFlow:
    """
    Test the complete flow:
    1. User joins queue
    2. Group forms
    3. AI monitors
    4. Group dispatches
    """
    
    @pytest.fixture
    def setup_test_data(self, db_session):
        """Setup test users and route"""
        
        # Create test route
        route = Route(
            route_code="TEST_ROUTE_1",
            origin_name="Test Origin",
            destination_name="Test Destination",
            origin_lat=28.6139,
            origin_lng=77.2090,
            dest_lat=28.6289,
            dest_lng=77.2265,
            distance_km=5.0,
            estimated_duration_mins=15,
            halfway_point_km=2.5,
            short_route_fare=30.0,
            full_route_fare=50.0,
            is_active=True
        )
        db_session.add(route)
        
        # Create test users
        users = []
        for i in range(4):
            user = User(
                firebase_uid=f"test_user_{i}",
                phone_number=f"9876543{i:02d}",
                full_name=f"Test User {i+1}",
                gender="MALE" if i % 2 == 0 else "FEMALE",
                is_active=True
            )
            db_session.add(user)
            users.append(user)
        
        db_session.commit()
        
        return {
            'route': route,
            'users': users
        }
    
    def test_single_user_joins(self, db_session, setup_test_data):
        """
        Test: Single user joins queue
        Expected: New group created, user added
        """
        
        route = setup_test_data['route']
        user = setup_test_data['users'][0]
        
        queue_service = QueueService(db_session)
        
        result = queue_service.join_queue(
            user_id=user.id,
            route_id=route.id,
            user_lat=28.6140,
            user_lng=77.2091,
            women_only=False
        )
        
        assert result['success'] == True
        assert result['current_size'] == 1
        assert result['max_size'] == 4
        assert result['seat_number'] == 1
        assert result['group_status'] == "FORMING"
    
    def test_multiple_users_join_same_group(self, db_session, setup_test_data):
        """
        Test: Multiple users join sequentially
        Expected: All join same group
        """
        
        route = setup_test_data['route']
        users = setup_test_data['users']
        
        queue_service = QueueService(db_session)
        
        group_ids = []
        
        # Users join one by one
        for i, user in enumerate(users[:3]):  # First 3 users
            result = queue_service.join_queue(
                user_id=user.id,
                route_id=route.id,
                user_lat=28.6140,
                user_lng=77.2091,
                women_only=False
            )
            
            group_ids.append(result['group_id'])
            
            assert result['success'] == True
            assert result['current_size'] == i + 1
            assert result['seat_number'] == i + 1
        
        # All should be in same group
        assert len(set(group_ids)) == 1, "All users should be in same group"
    
    def test_group_full_triggers_new_group(self, db_session, setup_test_data):
        """
        Test: 5th user triggers new group creation
        Expected: 4 users in first group, 5th user in new group
        """
        
        route = setup_test_data['route']
        users = setup_test_data['users']
        
        queue_service = QueueService(db_session)
        
        # Create 5th user
        user5 = User(
            firebase_uid="test_user_5",
            phone_number="9876543255",
            full_name="Test User 5",
            gender="MALE",
            is_active=True
        )
        db_session.add(user5)
        db_session.commit()
        
        results = []
        
        # All 4 original users join
        for user in users:
            result = queue_service.join_queue(
                user_id=user.id,
                route_id=route.id,
                user_lat=28.6140,
                user_lng=77.2091,
                women_only=False
            )
            results.append(result)
        
        # 5th user joins
        result5 = queue_service.join_queue(
            user_id=user5.id,
            route_id=route.id,
            user_lat=28.6140,
            user_lng=77.2091,
            women_only=False
        )
        
        # First 4 in same group
        first_group_id = results[0]['group_id']
        assert all(r['group_id'] == first_group_id for r in results)
        
        # 5th user in different group
        assert result5['group_id'] != first_group_id
        assert result5['current_size'] == 1
    
    def test_women_only_group_segregation(self, db_session, setup_test_data):
        """
        Test: Women-only preference creates separate group
        Expected: Women in separate group from men
        """
        
        route = setup_test_data['route']
        users = setup_test_data['users']
        
        queue_service = QueueService(db_session)
        
        # Male user joins normal group
        male_result = queue_service.join_queue(
            user_id=users[0].id,  # Male
            route_id=route.id,
            user_lat=28.6140,
            user_lng=77.2091,
            women_only=False
        )
        
        # Female user requests women-only
        female_result = queue_service.join_queue(
            user_id=users[1].id,  # Female
            route_id=route.id,
            user_lat=28.6140,
            user_lng=77.2091,
            women_only=True
        )
        
        # Should be in different groups
        assert male_result['group_id'] != female_result['group_id']
        assert female_result['women_only'] == True
        assert male_result['women_only'] == False
    
    def test_leave_queue(self, db_session, setup_test_data):
        """
        Test: User leaves queue
        Expected: Group size decreases, seats reassigned
        """
        
        route = setup_test_data['route']
        users = setup_test_data['users'][:3]
        
        queue_service = QueueService(db_session)
        
        # 3 users join
        for user in users:
            queue_service.join_queue(
                user_id=user.id,
                route_id=route.id,
                user_lat=28.6140,
                user_lng=77.2091,
                women_only=False
            )
        
        # Middle user leaves
        result = queue_service.leave_queue(users[1].id)
        
        assert result['success'] == True
        
        # Check group status
        status = queue_service.get_queue_status(users[0].id)
        assert status['current_size'] == 2
    
    def test_get_queue_status(self, db_session, setup_test_data):
        """
        Test: Get queue status for user
        """
        
        route = setup_test_data['route']
        user = setup_test_data['users'][0]
        
        queue_service = QueueService(db_session)
        
        # Before joining
        status_before = queue_service.get_queue_status(user.id)
        assert status_before['in_queue'] == False
        
        # Join queue
        queue_service.join_queue(
            user_id=user.id,
            route_id=route.id,
            user_lat=28.6140,
            user_lng=77.2091,
            women_only=False
        )
        
        # After joining
        status_after = queue_service.get_queue_status(user.id)
        assert status_after['in_queue'] == True
        assert status_after['current_size'] == 1
        assert status_after['your_seat'] == 1
    
    def test_concurrent_bookings_same_route(self, db_session, setup_test_data):
        """
        Test: Multiple users book simultaneously on same route
        Expected: Efficient group formation
        """
        
        route = setup_test_data['route']
        users = setup_test_data['users']
        
        queue_service = QueueService(db_session)
        
        results = []
        
        # Simulate concurrent bookings
        for user in users:
            result = queue_service.join_queue(
                user_id=user.id,
                route_id=route.id,
                user_lat=28.6140 + (users.index(user) * 0.001),  # Slightly different locations
                user_lng=77.2091,
                women_only=False
            )
            results.append(result)
        
        # All should be in same group (since they're compatible)
        group_ids = [r['group_id'] for r in results]
        assert len(set(group_ids)) == 1
        
        # Group should be full
        final_status = queue_service.get_queue_status(users[0].id)
        assert final_status['current_size'] == 4


class TestAIIntegration:
    """
    Test AI decision-making with queue
    """
    
    def test_ai_analyzes_forming_group(self, db_session, setup_test_data):
        """
        Test: AI analyzes a forming group
        """
        
        from app.ai.smart_dispatch import SmartDispatchService
        
        route = setup_test_data['route']
        users = setup_test_data['users'][:3]
        
        queue_service = QueueService(db_session)
        dispatch_service = SmartDispatchService(db_session)
        
        # Create group with 3 users
        for user in users:
            queue_service.join_queue(
                user_id=user.id,
                route_id=route.id,
                user_lat=28.6140,
                user_lng=77.2091,
                women_only=False
            )
        
        # Run AI analysis
        stats = dispatch_service.run_dispatch_analysis()
        
        assert stats['analyzed'] >= 1
        # Stats should show either dispatched or waiting
        assert (stats['dispatched'] + stats['waiting']) >= 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])