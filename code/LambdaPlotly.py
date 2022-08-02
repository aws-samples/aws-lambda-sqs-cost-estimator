# TIP: install plotly using pip3 install plotly==5.7.0
import configparser
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Constants for calcuations
DAYS_IN_MONTH = 30.41 # Avg days in Month
MAX_LAMBDA_MEMORY = 4096 # 4GB
COMPUTE_CHARGE_GBS_X86 = 0.0000166667
COMPUTE_CHARGE_GBS_ARM = 0.0000133334
REQUESTS_CHARGE_MONTHLY = 0.0000002
FREE_TIER_GBS = 400000  # 400GiB free memory per month
FREE_REQUESTS = 1000000 # 1 Million free requests per month


def load_properties(filepath, sep='=', comment_char='#'):
    """
    Read the file passed as parameter as a properties file.
    """
    props = {}
    with open(filepath, "rt") as f:
        for line in f:
            l = line.strip()
            if l and not l.startswith(comment_char):
                key_value = l.split(sep)
                key = key_value[0].strip()
                value = sep.join(key_value[1:]).strip().strip('"')
                props[key] = int(value)
    return props

def invocations_for_range(message_vol_range, batch_size = 1):
    invocations = []
    for vol in message_vol_range:
        invocations.append(vol *1000/batch_size)

    return invocations

def calculate_cost_for_message_vol_range(message_vol_range, invocation_memory, duration_sec, is_x86, batch_size = 1):
    cost = []
    for vol in message_vol_range:
        cost.append(calculate_monthly_cost(vol, invocation_memory, duration_sec, is_x86, batch_size))

    return cost

def calculate_requests_per_month(million_vol_per_day, batch_size):
    return (million_vol_per_day * 1000000 * DAYS_IN_MONTH/batch_size)

def calculate_total_gbs_per_month(requests_per_month, invocation_memory, duration_sec):
    return (invocation_memory * requests_per_month * duration_sec)

def calculate_monthly_cost(message_vol_millions_per_day, invocation_memory, duration_sec, is_x86, batch_size = 1):
    requests_per_month = calculate_requests_per_month(message_vol_millions_per_day, batch_size)
    total_memory_gbs = calculate_total_gbs_per_month(requests_per_month, invocation_memory, duration_sec)

    compute_charge_gbs = COMPUTE_CHARGE_GBS_X86
    if (not is_x86):
        compute_charge_gbs = COMPUTE_CHARGE_GBS_ARM

    usage_charge_per_month_after_free_tier = (total_memory_gbs - FREE_TIER_GBS) * compute_charge_gbs
    if (usage_charge_per_month_after_free_tier < 0):
        usage_charge_per_month_after_free_tier = 0
    requests_per_month_after_free_tier = (requests_per_month - FREE_REQUESTS) * REQUESTS_CHARGE_MONTHLY
    if (requests_per_month_after_free_tier < 0):
        requests_per_month_after_free_tier = 0

    total_monthly_charge = usage_charge_per_month_after_free_tier + requests_per_month_after_free_tier
    # print('Batch: ' + str(batch_size) + ', message_vol_millions_per_day' + str(message_vol_millions_per_day)
    #         + ', Request per month: ' + str(requests_per_month) + ' and memory: ' + str(total_memory_gbs) + ', is_x86: ' + str(is_x86)
    #         + ', usage charge: ' + str(usage_charge_per_month_after_free_tier) + ', request charge:' + str(requests_per_month_after_free_tier)
    #         + ', total charge: ' + str(total_monthly_charge) )

    return total_monthly_charge

def find_allowed_memory_setting(allowed_memory_range, requested_memory):
    for memory in allowed_memory_range:
        #print("Requested: " + str(requested_memory) + " and current allowed: " + str(memory))
        if requested_memory <= memory:
            return memory

    return allowed_memory_range[len(allowed_memory_range)-1]

def build_memory_range():
    potential_memory_ranges = []
    cur_memory = base_lambda_memory_mb
    while cur_memory <= MAX_LAMBDA_MEMORY:
        potential_memory_ranges.append(cur_memory)
        cur_memory += memory_increments
    return potential_memory_ranges

def build_batch_range():
    batch_range = []
    possible_batch_ranges = [ 1, 5, 10, 20, 50, 100, 200, 400, 500, 600, 1000, 1500, 2000, 5000, 10000 ]

    for batch_size in possible_batch_ranges:
        if batch_size <= max_batch_size:
            batch_range.append(batch_size)
    return batch_range

def report_input_params(fig, configMap):
    keys = list(configMap.keys())
    values = list(configMap.values())
    print('Input args: {}'.format(keys))
    print('Input values: {}'.format(values))
    fig.add_trace(go.Table(header=dict(values=['Input Parameter', 'Value']), cells=dict(values=[keys, values])),
        row=4, col=1   )

def plot_batch_size_vs_duration(fig, messages_per_day, recurring_batch_set, requests_per_day_using_batch, requests_per_month,
                    invocation_memory_range_as_mb, duration_range_as_ms, total_gbs_per_month,
                    monthly_cost_for_x86, monthly_cost_for_arm):

    fig.add_trace(go.Table(header=dict(values=['Messages Per Day', 'SQS Batch Size', 'Request per Day using Batch', 'Request Per Month',
                                               'Memory (MB) Per Invocation', 'Duration (ms) per batch', 'Total Memory (GBs) per Month',
                                               '$ Cost for x86 (requests & GBs after free tier)', '$ Cost for ARM (requests & GBs after free tier)']),
                            cells=dict(values=[messages_per_day, recurring_batch_set, requests_per_day_using_batch, requests_per_month,
                                                invocation_memory_range_as_mb, duration_range_as_ms, total_gbs_per_month,
                                                monthly_cost_for_x86, monthly_cost_for_arm ])),

        row=2, col=1   )

    #print("Invocation memory range: " + str(invocation_memory_range_as_mb))
    #print("Duration range:" + str(duration_range_as_ms))


    fig.add_trace(
        go.Scatter(x=batch_range, y=invocation_memory_range_as_mb, name="Invocation Memory (MB) with SQS Batch "),
        row=3, col=1, secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(x=batch_range, y=duration_range_as_ms, name="Invocation Duration (ms) with SQS Batch "),
        row=3, col=1, secondary_y=True,
    )
    fig.update_xaxes(title_text="SQS Batch Size", row=3)
    fig.update_yaxes(title_text="<b>Memory (MB) with SQS Batch</b>", row=3, secondary_y=False)
    fig.update_yaxes(title_text="<b>Duration (ms) with SQS Batch</b>", row=3, secondary_y=True)

def plot_cost_per_batch(fig, batch_size, million_invocations_per_day, cost_per_month_x86, cost_per_month_arm ):
        # Add traces
        fig.add_trace(
            go.Scatter(x=million_invocations_per_day, y=cost_per_month_x86, name="Cost for x86 with SQS Batch size: " + str(batch_size)),
            row=1, col=1, secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(x=million_invocations_per_day, y=cost_per_month_arm, name="Cost for ARM with SQS Batch size: " + str(batch_size)),
            row=1, col=1, secondary_y=False,
        )

        #
        # fig.add_trace(
        #     go.Scatter(x=million_invocations_per_day, y=invocations, name="Invocations (in 1000) per day with Batch: " + str(batch_size)),
        #     row=2, col=1, secondary_y=False,
        # )
        #
        # fig.add_trace(
        #     go.Scatter(x=million_invocations_per_day, y=invocations, name="Invocations (in 1000) per day with Batch: " + str(batch_size)),
        #     row=2, col=1, secondary_y=True,
        # )


        # Add figure title
        fig.update_layout(
            title_text="Monthly Cost vs Performance for SQS Message Batch Processing using Lambda (" + str(datetime.datetime.now()) + ")"
        )

        # Set x-axis title
        fig.update_xaxes(title_text="SQS Million Messages per Day", row=1)

        # Set y-axes titles
        fig.update_yaxes(title_text="<b>Cost Per Month ($)</b>", row=1, secondary_y=False)
        # fig.update_yaxes(title_text="<b>Invokes (In Thousands) per day using Batch</b>", row=2, secondary_y=True)

config = load_properties("input.prop")
base_lambda_memory_mb = config['base_lambda_memory_mb']
process_duration_per_message = config['process_per_message_ms']
warm_latency_ms = config['warm_latency_ms']
max_batch_size = config['max_batch_size']
batch_memory_overhead_mb = config['batch_memory_overhead_mb']
batch_increment = config['batch_increment']
memory_increments = 128

batch_range = build_batch_range()
potential_memory_ranges = build_memory_range()

def processCalculations():
    duration_range_as_ms = []
    invocation_memory_range_as_mb = []
    requests_per_day_using_batch = []
    messages_per_day = []
    requests_per_month = []
    total_gbs_per_month = []
    recurring_batch_set = []
    monthly_cost_for_x86 = []
    monthly_cost_for_arm = []

    million_invocations_per_day = [0.1, 0.5, 1, 5, 10, 15, 20, 50, 100, 200, 250]

    fig = make_subplots(rows=4, cols=1,
                        specs=[ [{"secondary_y": True}], [{"type": "table"}], [{"secondary_y": True}], [{"type": "table"}] ])

    # iterate over batch size and figure out the memory, duration, cost for x86 vs Graviton
    for batch_size in batch_range:
        duration_msec = warm_latency_ms + (process_duration_per_message*batch_size)

        invocation_memory = base_lambda_memory_mb

        # Based on batch size, calculate increased in function memory compared to base function memory
        required_memory_in_mb = base_lambda_memory_mb + batch_memory_overhead_mb * ((int) (batch_size / batch_increment))
        invocation_memory_in_mb = find_allowed_memory_setting(potential_memory_ranges, required_memory_in_mb)
        #print("Requested: " + str(required_memory_in_mb) + " for batch: " + str(batch_size) + " and got: " + str(invocation_memory_in_mb))
        cost_per_month_x86 = calculate_cost_for_message_vol_range(million_invocations_per_day, invocation_memory_in_mb/1024, duration_msec/1000, True, batch_size)
        cost_per_month_arm = calculate_cost_for_message_vol_range(million_invocations_per_day, invocation_memory_in_mb/1024, duration_msec/1000, False, batch_size)

        invocations = invocations_for_range(million_invocations_per_day, batch_size)

        #print("Batch: " + str(batch_size) + ", Memory: " + str(invocation_memory_in_mb) + ", Cost Per Month: " + str(cost_per_month_x86) + ", cost for ARM: " + str(cost_per_month_arm) + ", invocation: " + str(invocations))

        messages_per_day.append(10000000)
        recurring_batch_set.append(batch_size)
        invocation_memory_range_as_mb.append(invocation_memory_in_mb)
        duration_range_as_ms.append(duration_msec)
        requests_per_day_using_batch.append(str(10000000/batch_size))
        request_monthly = calculate_requests_per_month(10, batch_size)
        gbs_per_month = calculate_total_gbs_per_month(request_monthly, invocation_memory_in_mb/1024, duration_msec/1000)

        requests_per_month.append(request_monthly)
        total_gbs_per_month.append("{:.2f}".format(calculate_total_gbs_per_month(request_monthly, invocation_memory_in_mb/1024, duration_msec/1000)))

        usage_per_month_after_free_tier = (gbs_per_month - FREE_TIER_GBS)
        requests_per_month_after_free_tier = (request_monthly - FREE_REQUESTS)

        # Check if the usage falls under free tier for a month
        if (usage_per_month_after_free_tier < 0):
            usage_per_month_after_free_tier = 0
        if (requests_per_month_after_free_tier < 0):
            requests_per_month_after_free_tier = 0

        monthly_cost_for_x86.append(str("{:.2f}".format(usage_per_month_after_free_tier*COMPUTE_CHARGE_GBS_X86 + requests_per_month_after_free_tier*REQUESTS_CHARGE_MONTHLY)))
        monthly_cost_for_arm.append(str("{:.2f}".format(usage_per_month_after_free_tier*COMPUTE_CHARGE_GBS_ARM + requests_per_month_after_free_tier*REQUESTS_CHARGE_MONTHLY)))

        # Plot for graph for batch vs monthly cost
        plot_cost_per_batch(fig, batch_size, million_invocations_per_day, cost_per_month_x86, cost_per_month_arm )

    # Plot duration for handling vs batch size
    plot_batch_size_vs_duration(fig, messages_per_day, recurring_batch_set, requests_per_day_using_batch, requests_per_month,
                        invocation_memory_range_as_mb, duration_range_as_ms, total_gbs_per_month,
                        monthly_cost_for_x86, monthly_cost_for_arm)
    report_input_params(fig, config)
    fig.show()

    return fig

def main():
    processCalculations()

if __name__ == "__main__":
    main()
