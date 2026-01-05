import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd())))

from src.infrastructure.llm_gateway import LLMGatewayImpl


def test_llm():
    print("Initializing LLM Gateway...")
    try:
        gateway = LLMGatewayImpl()
        if (
            gateway.provider == "openai"
            and hasattr(gateway, "openai_base_url")
            and gateway.openai_base_url
        ):
            print(f"Base URL: {gateway.openai_base_url}")
        print(f"Provider: {gateway.provider}")
        print(f"Model: {gateway.model_name}")

        print("\nTesting simple prompt...")
        # Simple test to check contradiction
        result = gateway.check_text_contradiction(
            "The sky is blue.", "The sky is green."
        )
        print(f"Result: {result}")

        if result and isinstance(result, dict):
            print("\nSUCCESS: LLM responded correctly.")
        else:
            print("\nFAILURE: Unexpected response format.")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_llm()
