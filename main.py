"""Paper Summary Pipeline - Main entry point with modular steps"""
import os
import sys

# Disable Chroma telemetry BEFORE any imports that use chromadb
os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from module.pipeline import Pipeline


def main():
    """Main entry point - launches interactive pipeline"""
    pipeline = Pipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
