#!/usr/bin/env python3
"""
Interactive Test Client for Quotebot AI Proxy
Tests the complete conversation flow
"""

import httpx
import json
import sys
import time
from typing import Optional


class Colors:
    """Terminal colors"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class QuotebotTestClient:
    """Test client for Quotebot API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
        self.conversation_id: Optional[str] = None

    def print_section(self, title: str):
        """Print section header"""
        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}{title}{Colors.END}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.END}\n")

    def print_success(self, message: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓{Colors.END} {message}")

    def print_error(self, message: str):
        """Print error message"""
        print(f"{Colors.RED}✗{Colors.END} {message}")

    def print_info(self, message: str):
        """Print info message"""
        print(f"{Colors.CYAN}ℹ{Colors.END} {message}")

    def print_json(self, data: dict):
        """Pretty print JSON"""
        print(f"{Colors.BLUE}{json.dumps(data, indent=2)}{Colors.END}")

    def test_health(self):
        """Test health endpoint"""
        self.print_section("1. Testing Health Endpoint")

        try:
            response = self.client.get(f"{self.base_url}/health")
            response.raise_for_status()

            data = response.json()
            self.print_success("Health check passed")
            self.print_json(data)

            return True
        except Exception as e:
            self.print_error(f"Health check failed: {str(e)}")
            return False

    def start_conversation(self):
        """Test start conversation"""
        self.print_section("2. Starting Conversation")

        payload = {
            "session_id": f"test-{int(time.time())}",
            "user_data": {
                "is_identified_user": True,
                "name": "Test User",
                "email": "test@example.com"
            },
            "traffic_data": {
                "traffic_source": "test_script",
                "landing_page": "/test"
            }
        }

        self.print_info("Sending request...")
        self.print_json(payload)

        try:
            response = self.client.post(
                f"{self.base_url}/api/v1/start_conversation",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            self.conversation_id = data.get("conversation_id")

            self.print_success(f"Conversation started: {self.conversation_id}")
            self.print_json(data)

            return True
        except Exception as e:
            self.print_error(f"Failed to start conversation: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.print_error(f"Response: {e.response.text}")
            return False

    def send_message(self, message: str):
        """Send a message"""
        if not self.conversation_id:
            self.print_error("No active conversation. Start one first.")
            return False

        print(f"\n{Colors.YELLOW}User:{Colors.END} {message}")

        payload = {
            "conversation_id": self.conversation_id,
            "message": message
        }

        try:
            response = self.client.post(
                f"{self.base_url}/api/v1/chat",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            answer = data.get("answer", "")
            complete = data.get("conversation_complete", False)

            print(f"{Colors.GREEN}AI:{Colors.END} {answer}")

            if complete:
                print(f"\n{Colors.BOLD}{Colors.YELLOW}🎉 Conversation Complete!{Colors.END}")

            return True
        except Exception as e:
            self.print_error(f"Failed to send message: {str(e)}")
            if hasattr(e, 'response') and e.response:
                self.print_error(f"Response: {e.response.text}")
            return False

    def get_history(self):
        """Get conversation history"""
        self.print_section("4. Fetching Conversation History")

        if not self.conversation_id:
            self.print_error("No active conversation")
            return False

        try:
            response = self.client.get(
                f"{self.base_url}/api/v1/history/{self.conversation_id}"
            )
            response.raise_for_status()

            messages = response.json()

            self.print_success(f"Retrieved {len(messages)} messages")

            for i, msg in enumerate(messages, 1):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                if role == "user":
                    print(f"{Colors.YELLOW}[{i}] User:{Colors.END} {content}")
                else:
                    print(f"{Colors.GREEN}[{i}] AI:{Colors.END} {content}")

            return True
        except Exception as e:
            self.print_error(f"Failed to get history: {str(e)}")
            return False

    def interactive_chat(self):
        """Interactive chat mode"""
        self.print_section("3. Interactive Chat")

        self.print_info("Type your messages (or 'quit' to exit)")
        print()

        while True:
            try:
                user_input = input(f"{Colors.YELLOW}You:{Colors.END} ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    break

                if not self.send_message(user_input):
                    break

                print()

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break

    def run_full_test(self):
        """Run complete test flow"""
        print(f"{Colors.BOLD}{Colors.HEADER}")
        print("=" * 60)
        print("  Quotebot AI Proxy - Test Client")
        print("=" * 60)
        print(f"{Colors.END}\n")

        self.print_info(f"Testing: {self.base_url}")

        # Test health
        if not self.test_health():
            self.print_error("Health check failed. Is the service running?")
            return

        # Start conversation
        if not self.start_conversation():
            self.print_error("Failed to start conversation")
            return

        # Interactive chat
        self.interactive_chat()

        # Get history
        self.get_history()

        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}Test Complete!{Colors.END}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.END}\n")

    def run_automated_test(self):
        """Run automated test with predefined messages"""
        print(f"{Colors.BOLD}{Colors.HEADER}")
        print("=" * 60)
        print("  Quotebot AI Proxy - Automated Test")
        print("=" * 60)
        print(f"{Colors.END}\n")

        # Test health
        if not self.test_health():
            return

        # Start conversation
        if not self.start_conversation():
            return

        # Predefined messages
        messages = [
            "Hello, I'm looking for equipment",
            "I need forklifts",
            "2 diesel forklifts",
            "4 meters lifting height",
            "3 ton capacity",
            "My name is John Doe",
            "john.doe@company.com"
        ]

        self.print_section("3. Sending Automated Messages")

        for i, message in enumerate(messages, 1):
            self.print_info(f"Message {i}/{len(messages)}")
            if not self.send_message(message):
                break
            time.sleep(1)  # Wait 1 second between messages
            print()

        # Get history
        self.get_history()

        print(f"\n{Colors.HEADER}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}Automated Test Complete!{Colors.END}")
        print(f"{Colors.HEADER}{'=' * 60}{Colors.END}\n")


def main():
    """Main function"""
    # Parse command line arguments
    base_url = "http://localhost:8000"
    mode = "interactive"

    if len(sys.argv) > 1:
        if sys.argv[1].startswith("http"):
            base_url = sys.argv[1]
        elif sys.argv[1] in ["auto", "automated"]:
            mode = "automated"

    if len(sys.argv) > 2:
        if sys.argv[2] in ["auto", "automated"]:
            mode = "automated"
        elif sys.argv[2].startswith("http"):
            base_url = sys.argv[2]

    # Create client
    client = QuotebotTestClient(base_url)

    # Run test
    if mode == "automated":
        client.run_automated_test()
    else:
        client.run_full_test()


if __name__ == "__main__":
    main()
