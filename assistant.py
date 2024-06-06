import json
from openai import OpenAI
import time
import os
from datetime import datetime
import slack_sdk
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt import App
import requests
import elasticsearch7

# Environment Variables for Configuration
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")
GRAFANA_URL = os.getenv("GRAFANA_URL")
PROMETHEUS_DATASOURCE_ID = os.getenv("PROMETHEUS_DATASOURCE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")

# constants
NAME = "name"
ONCALL_ASSISTANT_ID = "openai assistant id once created"

THREADS = {}

# Clients
slack_app = App(token=SLACK_APP_TOKEN)
slack_client = slack_sdk.WebClient(token=SLACK_BOT_TOKEN)
# OpenAI setup
openai_client = OpenAI(api_key=OPENAI_API_KEY)
# ElasticSearch setup
ES = elasticsearch7.Elasticsearch(ELASTICSEARCH_URL)


def show_json(obj):
    print(json.loads(obj.model_dump_json()))


# OpenAI assistant creation - one time call
# assistant = openai_client.beta.assistants.create(
#    name="OnCall helper",
#    instructions="You are an oncall assistant. you will fetch data from multiple sources and help an OPs engineer to understand what is the current status of a production environment. answers should be 1-2 sentences max",
#    model="gpt-4-1106-preview",
# )

# show_json(assistant)


def submit_message(assistant_id, thread, user_message):
    openai_client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_message
    )
    return openai_client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )


def get_response(thread):
    return openai_client.beta.threads.messages.list(thread_id=thread.id, order="desc").data[0]


def get_messages(thread):
    return openai_client.beta.threads.messages.list(thread_id=thread.id, order="asc")


def create_thread_and_run(user_input):
    thread = openai_client.beta.threads.create()
    run = submit_message(ONCALL_ASSISTANT_ID, thread, user_input)
    return thread, run


def get_or_create_thread(thread_id):
    if thread := THREADS.get(thread_id):
        return thread
    else:
        thread = openai_client.beta.threads.create()
    THREADS[thread_id] = thread
    return thread


def create_thread():
    thread = openai_client.beta.threads.create()
    return thread


# Pretty printing helper
def pretty_print(messages):
    print("# Messages")
    for m in messages:
        print(f"{m.role}: {m.content[0].text.value}")
    print()


def message_pretty_print(message):
    print("# Message")
    print(f"{message.role}: {message.content[0].text.value}")
    print()


# Waiting in a loop
def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run


# Function to fetch messages from the last hours from a Slack channel
def fetch_messages_from_past_day(hours=24):
    current_time = int(datetime.now().timestamp())  # Current time in seconds since epoch
    one_week_ago = current_time - (hours * 60 * 60)  # Time in seconds since epoch

    # production-critical-alert slack channel
    channel_id = '<slack chanel id>'

    try:
        response = slack_client.conversations_history(
            channel=channel_id,
            oldest=one_week_ago,
            limit=1000  # Adjust this based on your expected volume
        )
        if response["ok"]:
            return response['messages']
        else:
            raise Exception(f"Error fetching messages: {response['error']}")
    except slack_sdk.errors.SlackApiError as e:
        print(f"Error fetching messages: {e.response['error']}")


def check_webpage_accessibility(*args, **kwargs):
    # placeholder for a function verify your webpage is accessible
    return


def container_logs(container=None, log_count=10):
    seen = set()
    query = {'query': {'bool': {'filter': [{'term': {'kubernetes.container.name': f'{container}'}},
                                           {'range': {'@timestamp': {'gte': 'now-15m'}}}]}}}

    response = ES.search(index='logs-*', body=query, size=log_count)
    for doc in response['hits']['hits']:
        if 'message' in doc['_source']:
            msg = doc['_source']['message']
            if msg in seen:
                continue
            seen.add(msg)
    return seen


def grafana_kafka_lag_query(consumer_group=None):
    # Headers for authentication
    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }
    # Prepare the query
    payload = {
        "from": "now-6h",
        "to": "now",
        "queries": [
            {
                "refId": "A",
                "datasourceId": PROMETHEUS_DATASOURCE_ID,
                "expr": f'max(kafka_consumergroup_lag_sum{{consumergroup="{consumer_group}"}}) by (consumergroup, topic) > 0',
                "format": "time_series",
                "interval": "1m"
            }
        ]
    }

    # Grafana API endpoint for querying
    query_url = f"{GRAFANA_URL}/api/ds/query"
    # Query the data

    # Make the request
    response = requests.post(query_url, headers=headers, data=json.dumps(payload))

    print(response.json())
    return response.json()


function_fetch_messages_json = {
    "name": "fetch_messages_from_past_day",
    "description": "Fetch last day slack messages of grafana, prometheus and other monitoring tools related to our production environment",
    "parameters": {
        "type": "object",
        "properties": {
            "hours": {"type": "number", "description": "amount of hours to go back the fetch messages since"},
        },
        "required": ["hours"],
    }
}

function_check_webpage_json = {
    "name": "check_webpage_accessibility",
    "description": "check if system is available. return the status code in case its not accessible",
}

function_check_container_logs_json = {
    "name": "container_logs",
    "description": "fetch from the elasticsearch monitoring the last container logs",
    "parameters": {
        "type": "object",
        "properties": {
            "container": {"type": "string", "description": "the container name"},
            "log_count": {"type": "number", "description": "amount of logs to return"},
        },
        "required": ["container", "log_count"],
    }

}

function_kafka_lag_query_json = {
    "name": "grafana_kafka_lag_query",
    "description": "fetch the latest grafana kafka lag data about the given consumer group",
    "parameters": {
        "type": "object",
        "properties": {
            "consumer_group": {"type": "string", "description": "the kafka consumer group"},
        },
        "required": ["consumer_group"],
    }

}

assistant = openai_client.beta.assistants.update(
    ONCALL_ASSISTANT_ID,
    tools=[
        {"type": "code_interpreter"},
        {"type": "file_search"},
        {"type": "function", "function": function_fetch_messages_json},
        {"type": "function", "function": function_check_webpage_json},
        {"type": "function", "function": function_check_container_logs_json},
        {"type": "function", "function": function_kafka_lag_query_json},

    ],
)
FUNCTION_NAME_TO_FUNCTION = {
    function_kafka_lag_query_json[NAME]: grafana_kafka_lag_query,
    function_check_container_logs_json[NAME]: container_logs,
    function_check_container_logs_json[NAME]: check_webpage_accessibility,
    function_fetch_messages_json[NAME]: fetch_messages_from_past_day
}


# This gets activated when the bot is tagged in a channel
@slack_app.event("app_mention")
def handle_message_events(body, logger):
    # Log message
    print(str(body["event"]["text"]))
    print(str(body["event"]["text"]).split(">")[1])

    print("event is: ", str(body["event"]))

    if 'thread_ts' in body["event"]:
        print("Slack Thread: ", body["event"]["thread_ts"])
        thread = get_or_create_thread(body["event"]["thread_ts"])
    else:
        print("Slack event: ", body["event"]["event_ts"])
        thread = get_or_create_thread(body["event"]["event_ts"])

    print("Thread id is: ", thread)
    # Create prompt for ChatGPT
    prompt = str(body["event"]["text"]).split(">")[1]

    # Let the user know that we are busy with the request
    response = slack_client.chat_postMessage(channel=body["event"]["channel"],
                                             thread_ts=body["event"]["event_ts"],
                                             text=f":robot_face: \nOn it!")

    run = submit_message(ONCALL_ASSISTANT_ID, thread, prompt)
    run = wait_on_run(run, thread)
    print(run.status)

    while run.required_action is not None:
        # Extract tool call
        tool_calls = run.required_action.submit_tool_outputs.tool_calls

        print("Calling tools: ", len(tool_calls), tool_calls)
        # Extract single tool call
        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            print("Function Name:", name)
            print("Function Arguments:", arguments)

            if handler := FUNCTION_NAME_TO_FUNCTION.get(name):
                response = handler(**arguments)
                tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(response)})
                # print the responses
                print("The response is: ", json.dumps(response))

        run = openai_client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread.id,
            run_id=run.id,
            tool_outputs=tool_outputs,
        )

        show_json(run)

        run = wait_on_run(run, thread)
        print(run.status)

    pretty_print(get_messages(thread))
    bot_response = get_response(thread)

    # Reply to thread
    slack_client.chat_postMessage(channel=body["event"]["channel"],
                                  thread_ts=body["event"]["event_ts"],
                                  text=f":heart: \n{bot_response.content[0].text.value}")


if __name__ == "__main__":
    SocketModeHandler(slack_app, SLACK_APP_TOKEN).start()
