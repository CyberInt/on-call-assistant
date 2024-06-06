# on-call-assistant
The On-Call Assistant for Slack is a sophisticated bot designed to enhance the monitoring and troubleshooting of production environments. Built with the integration of OpenAI's powerful Assistant, this tool specializes in real-time assistance and proactive engagement. The assistant is triggered by mentions, offering a flexible approach to monitoring that can be adapted to automatically react to specific messages if required. This solution employs OpenAI's "functions" to seamlessly interact with various operational tools, facilitating tasks such as log retrieval from ElasticSearch, Grafana and Prometheus statistics fetching, and SaaS system accessibility checks.


**This repository houses a conceptual prototype, showcasing the potential application of such technology in real-world scenarios.**

## Features
- **Real-Time Monitoring**: Leverages the capabilities of the OpenAI Assistant to provide instant monitoring and alerts.
- **Flexible Trigger Mechanism**: Configurable to respond to mentions or automatically act upon detecting specific messages in Slack.
- **Integrated Tools Support**: Includes built-in functions for interacting with logs, Grafana, Prometheus, and SaaS systems for comprehensive environment oversight.
- **Customizable Actions**: Offers the ability to tailor the assistant's responses and actions to fit specific monitoring and troubleshooting needs.

## Getting Started
To get started with the On-Call Assistant, follow these steps:

### Prerequisites
- Ensure you have a GitHub account and Git installed on your machine.
- An active OpenAI API key is required to interact with the OpenAI Assistant.
- Slack App should be configured with the proper permissions to listen for app_mention events

### Installation
1. Clone the repository
2. Run the following
```pip install -r requirements.txt
```

### Configuration
Configure the OpenAI Assistant API key in your environment variables or project settings, and set up the necessary integrations with ElasticSearch, Grafana, Prometheus, and any SaaS platforms you plan to monitor. Adjust the bot's listening and response behaviors according to your needs.

To create the assistant as a one-time setup, run the following code snippet with your relevant information:
```python
# OpenAI assistant creation - one time call
assistant = openai_client.beta.assistants.create(
 name="OnCall assistant",
 instructions="You are an oncall assistant. You will fetch data from multiple sources and help an Ops engineer understand the current status of a production environment. Answers should be 1-2 sentences max.",
 model="gpt-4-1106-preview",
)
```

## Contributing
Contributions to the On-Call Assistant are welcome!

## License
This project is licensed under the MIT License - see the `LICENSE.md` file for details.

## Acknowledgments
- This project was inspired by and utilized concepts from the OpenAI Cookbook, specifically the "Assistants API Overview (Python)" article. [OpenAI Cookbook: Assistants API Overview](https://cookbook.openai.com/examples/assistants_api_overview_python)
