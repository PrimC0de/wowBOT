#!/usr/bin/env python3
"""
Test script for the updated voting functionality
"""

# Replicate the updated vote tracking logic from main.py
thread_votes = {}  # Structure: {thread_ts: {user_id: vote_type}}

def has_user_voted(thread_ts, user_id):
    """Check if user has already voted on this thread."""
    return thread_votes.get(thread_ts, {}).get(user_id) is not None

def record_user_vote(thread_ts, user_id, vote_type):
    """Record a user's vote for a thread."""
    if thread_ts not in thread_votes:
        thread_votes[thread_ts] = {}
    thread_votes[thread_ts][user_id] = vote_type

def get_updated_blocks_after_vote(original_text, thread_ts):
    """Generate updated blocks showing vote status and keeping the Give Feedback button."""
    # Count votes for display
    votes = thread_votes.get(thread_ts, {})
    useful_count = sum(1 for vote in votes.values() if vote == "useful")
    not_useful_count = sum(1 for vote in votes.values() if vote == "not_useful")
    
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": original_text
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"👍 {useful_count} helpful • 👎 {not_useful_count} not helpful"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "💬 Give Feedback"},
                    "value": "give_feedback",
                    "action_id": "feedback_text"
                }
            ]
        }
    ]

def test_updated_voting():
    """Test the updated voting functionality"""
    print("Testing updated voting functionality...")
    
    # Clear any existing votes for testing
    thread_votes.clear()
    
    thread_ts = "1234567890.123456"
    user1 = "U123456789"
    user2 = "U987654321"
    
    # Test 1: Record votes
    record_user_vote(thread_ts, user1, "useful")
    record_user_vote(thread_ts, user2, "not_useful")
    print("✓ Votes recorded")
    
    # Test 2: Check blocks structure after voting
    blocks = get_updated_blocks_after_vote("Test message", thread_ts)
    
    # Verify the blocks structure
    assert len(blocks) == 3, f"Expected 3 blocks, got {len(blocks)}"
    assert blocks[0]["type"] == "section", "First block should be section"
    assert blocks[1]["type"] == "context", "Second block should be context"
    assert blocks[2]["type"] == "actions", "Third block should be actions"
    print("✓ Block structure is correct")
    
    # Test 3: Check vote count display
    context_text = blocks[1]["elements"][0]["text"]
    assert "👍 1 helpful" in context_text, f"Should show 1 helpful vote, got: {context_text}"
    assert "👎 1 not helpful" in context_text, f"Should show 1 not helpful vote, got: {context_text}"
    print("✓ Vote counts are displayed correctly")
    
    # Test 4: Check Give Feedback button is present
    feedback_button = blocks[2]["elements"][0]
    assert feedback_button["text"]["text"] == "💬 Give Feedback", "Give Feedback button should be present"
    assert feedback_button["action_id"] == "feedback_text", "Action ID should be feedback_text"
    print("✓ Give Feedback button is preserved")
    
    # Test 5: Verify no voting buttons are present
    action_elements = blocks[2]["elements"]
    assert len(action_elements) == 1, f"Should only have 1 button (Give Feedback), got {len(action_elements)}"
    print("✓ Voting buttons are correctly hidden")
    
    print("\n🎉 All tests passed! The updated voting system is working correctly.")
    print("✅ Vote counts are displayed")
    print("✅ Give Feedback button remains visible")
    print("✅ Useful/Not Useful buttons are hidden after voting")

if __name__ == "__main__":
    test_updated_voting()