#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import threading
import time
import sys
import os


class VelocityTestNode(Node):
    def __init__(self):
        super().__init__('velocity_test_node')
        
        # Create publisher for cmd_vel topic
        self.cmd_vel_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        
        # Initialize Twist message
        self.twist_msg = Twist()
        
        # Control variables
        self.is_publishing = False
        self.test_mode = None  # 'linear' or 'angular'
        self.ui_lock = threading.Lock()  # Prevent output conflicts
        
        # Reduce ROS2 log level to minimize console output during user input
        self.get_logger().set_level(rclpy.logging.LoggingSeverity.WARN)
        
        print("Velocity Test Node initialized")
        
        # Start the user interface in a separate thread
        self.ui_thread = threading.Thread(target=self.user_interface, daemon=True)
        self.ui_thread.start()

    def publish_velocity(self, linear_vel=0.0, angular_vel=0.0, duration=1.0):
        """
        Publish velocity for a specified duration
        """
        self.is_publishing = True
        
        # Set velocities
        self.twist_msg.linear.x = linear_vel
        self.twist_msg.linear.y = 0.0
        self.twist_msg.linear.z = 0.0
        self.twist_msg.angular.x = 0.0
        self.twist_msg.angular.y = 0.0
        self.twist_msg.angular.z = angular_vel
        
        with self.ui_lock:
            print(f'► Starting test - Linear: {linear_vel} m/s, Angular: {angular_vel} rad/s for {duration} seconds')
            print('► Test in progress...', end='', flush=True)
        
        # Record start time
        start_time = time.time()
        
        # Publish at 10 Hz during the duration
        rate = 10.0  # Hz
        sleep_time = 1.0 / rate
        
        while (time.time() - start_time) < duration and self.is_publishing:
            self.cmd_vel_publisher.publish(self.twist_msg)
            time.sleep(sleep_time)
        
        # Stop the robot
        self.stop_robot()
        
        with self.ui_lock:
            print(f'\r► Test completed! Published for {time.time() - start_time:.2f} seconds')
        
        self.is_publishing = False

    def stop_robot(self):
        """
        Send zero velocities to stop the robot
        """
        stop_msg = Twist()
        stop_msg.linear.x = 0.0
        stop_msg.linear.y = 0.0
        stop_msg.linear.z = 0.0
        stop_msg.angular.x = 0.0
        stop_msg.angular.y = 0.0
        stop_msg.angular.z = 0.0
        
        # Send stop command multiple times to ensure it's received
        for _ in range(5):
            self.cmd_vel_publisher.publish(stop_msg)
            time.sleep(0.1)

    def get_test_mode(self):
        """
        Get user's choice for test mode
        """
        while True:
            print("\n" + "="*50)
            print("ROS2 Velocity Test Node")
            print("="*50)
            print("Choose test mode:")
            print("1. Linear velocity test")
            print("2. Angular velocity test")
            print("3. Exit")
            
            try:
                choice = input("Enter your choice (1/2/3): ").strip()
                
                if choice == '1':
                    return 'linear'
                elif choice == '2':
                    return 'angular'
                elif choice == '3':
                    return 'exit'
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except KeyboardInterrupt:
                return 'exit'

    def get_linear_test_parameters(self):
        """
        Get linear velocity test parameters from user
        """
        while True:
            try:
                with self.ui_lock:
                    print("\n--- Linear Velocity Test ---")
                    velocity = float(input("Enter linear velocity (m/s): "))
                    duration = float(input("Enter duration (seconds): "))
                
                if duration <= 0:
                    with self.ui_lock:
                        print("Duration must be positive!")
                    continue
                    
                return velocity, duration
                
            except ValueError:
                with self.ui_lock:
                    print("Please enter valid numbers!")
            except KeyboardInterrupt:
                return None, None

    def get_angular_test_parameters(self):
        """
        Get angular velocity test parameters from user
        """
        while True:
            try:
                with self.ui_lock:
                    print("\n--- Angular Velocity Test ---")
                    velocity = float(input("Enter angular velocity (rad/s): "))
                    duration = float(input("Enter duration (seconds): "))
                
                if duration <= 0:
                    with self.ui_lock:
                        print("Duration must be positive!")
                    continue
                    
                return velocity, duration
                
            except ValueError:
                with self.ui_lock:
                    print("Please enter valid numbers!")
            except KeyboardInterrupt:
                return None, None

    def user_interface(self):
        """
        Main user interface loop
        """
        # First, get the test mode
        self.test_mode = self.get_test_mode()
        
        if self.test_mode == 'exit':
            self.get_logger().info('Exiting...')
            rclpy.shutdown()
            return
        
        # Main testing loop
        while rclpy.ok():
            try:
                if self.test_mode == 'linear':
                    velocity, duration = self.get_linear_test_parameters()
                    if velocity is not None and duration is not None:
                        # Run test in separate thread to avoid blocking
                        test_thread = threading.Thread(
                            target=self.publish_velocity,
                            args=(velocity, 0.0, duration)
                        )
                        test_thread.start()
                        test_thread.join()  # Wait for test to complete
                    else:
                        break
                        
                elif self.test_mode == 'angular':
                    velocity, duration = self.get_angular_test_parameters()
                    if velocity is not None and duration is not None:
                        # Run test in separate thread to avoid blocking
                        test_thread = threading.Thread(
                            target=self.publish_velocity,
                            args=(0.0, velocity, duration)
                        )
                        test_thread.start()
                        test_thread.join()  # Wait for test to complete
                    else:
                        break
                
                # Ask if user wants to continue
                with self.ui_lock:
                    print("\nTest completed!")
                    continue_choice = input("Continue testing? (y/n): ").strip().lower()
                if continue_choice not in ['y', 'yes']:
                    break
                    
            except KeyboardInterrupt:
                break
        
        with self.ui_lock:
            print('Shutting down velocity test node...')
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = VelocityTestNode()
        
        # Keep the node running
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.stop_robot()  # Ensure robot stops
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()