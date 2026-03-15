from llm_client import LLMClient

llm = LLMClient()

out = llm.generate_text("You are helpful.", "Say hello in one short line.")
print("RAW:", repr(out))
print("LEN:", len(out))