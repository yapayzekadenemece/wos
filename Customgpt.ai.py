from customgpt_client import CustomGPT
import uuid

# Set API key
CustomGPT.api_key = "7672|QXBCwlQqPuRVzrlc4advm4k9v1jYzKyzUVLz891teafab7a1"

# Create session ID
session_id = uuid.uuid4()

# Send conversation
stream_response = CustomGPT.Conversation.send(
    project_id="76464",
    session_id=session_id,
    prompt="Who is Tom Brady? Answer in 10 words only"
)

answer = stream_response.parsed.data.openai_response

print("Response:", answer)