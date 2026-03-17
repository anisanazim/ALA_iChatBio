from ichatbio.server import run_agent_server
from agent import ALAAgent

if __name__ == "__main__":
    agent = ALAAgent()
    print("Starting ALA agent at http://0.0.0.0:9999")
    run_agent_server(agent, host="0.0.0.0", port=9999)