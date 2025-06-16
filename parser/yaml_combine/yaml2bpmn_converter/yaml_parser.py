from .bpmn_object_models import *

# global counter for flow ids per playbook
_flow_id_counter = 0
_start_event_id_counter = 0
_end_event_id_counter = 0
_timer_event_definition_id_counter = 0

def _generate_sequence_flow_id() -> str:
    global _flow_id_counter
    _flow_id_counter += 1
    return f"sequenceFlow_{_flow_id_counter}"

def _generate_start_event_id() -> str:
    global _start_event_id_counter
    _start_event_id_counter += 1
    return f"startEvent_{_start_event_id_counter}"

def _generate_end_event_id() -> str:
    global _end_event_id_counter
    _end_event_id_counter += 1
    return f"endEvent_{_end_event_id_counter}"

def _generate_timer_event_definition_id() -> str:
    global _timer_event_definition_id_counter
    _timer_event_definition_id_counter += 1
    return f"timerEventDefinition_{_timer_event_definition_id_counter}"

def _add_implicit_start_end_events(bpmn_process_object: BPMNProcess | BPMNSubProcess):
    # remove any pre-existing start and end events
    bpmn_process_object.clean_start_end_events()

    if not bpmn_process_object.flow_elements:
        # process doesn't have any tasks
        # if it's a subprocess and it's truly empty, add "start->end" path
        if isinstance(bpmn_process_object, BPMNSubProcess) and not bpmn_process_object.flow_elements:
            start_event = BPMNStartEvent(id=f"{bpmn_process_object.id}_start")
            end_event = BPMNEndEvent(id=f"{bpmn_process_object.id}_end")
            start_end_flow = BPMNSequenceFlow(
                id=_generate_sequence_flow_id(),
                source_ref=start_event.id,
                target_ref=end_event.id
            )

            start_event.add_outgoing_flow(start_end_flow.id)
            end_event.add_incoming_flow(start_end_flow.id)

            bpmn_process_object.set_start_event(start_event)
            bpmn_process_object.add_end_event(end_event)
            bpmn_process_object.add_flow_element(start_event)
            bpmn_process_object.add_flow_element(end_event)
            bpmn_process_object.add_sequence_flow(start_end_flow)

    tasks_with_no_incoming = [
        task for task in bpmn_process_object.flow_elements if not task.incoming_flows
    ]
    tasks_with_no_outgoing = [
        task for task in bpmn_process_object.flow_elements if not task.outgoing_flows
    ]

    # add start event and all necessary sequence flows
    start_event_id = _generate_start_event_id()
    start_event = BPMNStartEvent(id=start_event_id)

    if not tasks_with_no_incoming: # all nodes have incoming -> connect to the first one
        tasks_to_connect_start = [bpmn_process_object.flow_elements[0]]
    else:
        tasks_to_connect_start = tasks_with_no_incoming

    for task in tasks_to_connect_start:
        flow_id = _generate_sequence_flow_id()
        sequence_flow = BPMNSequenceFlow(
            id=flow_id,
            source_ref=start_event.id,
            target_ref=task.id
        )
        start_event.add_outgoing_flow(flow_id)
        task.add_incoming_flow(flow_id)
        bpmn_process_object.add_sequence_flow(sequence_flow)

    bpmn_process_object.set_start_event(start_event)
    bpmn_process_object.add_flow_element(start_event)

    # add end event(s) and all necessary sequence flows
    if not tasks_with_no_outgoing: # all nodes have outgoing -> connect to the last one
        tasks_to_connect_end = [bpmn_process_object.flow_elements[-1]]
    else:
        tasks_to_connect_end = tasks_with_no_outgoing

    for task in tasks_to_connect_end:
        end_event_id = _generate_end_event_id()
        end_event = BPMNEndEvent(id=end_event_id)
        flow_id = _generate_sequence_flow_id()
        sequence_flow = BPMNSequenceFlow(
            id=flow_id,
            source_ref=task.id,
            target_ref=end_event.id
        )
        task.add_outgoing_flow(flow_id)
        end_event.add_incoming_flow(flow_id)
        bpmn_process_object.add_sequence_flow(sequence_flow)
        bpmn_process_object.add_end_event(end_event)
        bpmn_process_object.add_flow_element(end_event)

def _parse_activities_recursive(activities: dict) -> tuple[list[BPMNFlowElement], list[BPMNSequenceFlow]]:
    flow_elements: list[BPMNFlowElement] = []
    sequence_flows: list[BPMNSequenceFlow] = []
    # map for getting the flow element by its id
    task_map: dict[str, BPMNFlowElement] = {}

    ## looping twice over the activities
    ### first loop: getting tasks
    for activity_id, activity_data in activities.items():
        name = activity_data.get("name", activity_id)
        activity_type = activity_data.get("type")

        bpmn_task: BPMNTask = None

        if activity_type == "human":
            bpmn_task = BPMNUserTask(id=activity_id, name=name)
        elif activity_type == "send":
            bpmn_task = BPMNSendTask(id=activity_id, name=name)
        elif activity_type == "manual":
            bpmn_task = BPMNManualTask(id=activity_id, name=name)
        elif activity_type == "intimer":
            timer_event_definition_id = _generate_timer_event_definition_id()
            bpmn_task = BPMNIntimerEvent(id=activity_id, name=name, timer_event_definition_id=timer_event_definition_id)
        elif activity_type == "xgw":
            bpmn_task = BPMNExclusiveGateway(id=activity_id, name=name)
        elif activity_type == "sub":
            sub_process = BPMNSubProcess(id=activity_id, name=name)
            inner_activities = activity_data.get("activities", {})
            inner_flow_elements, inner_sequence_flows = _parse_activities_recursive(
                inner_activities
            )
            sub_process.flow_elements = inner_flow_elements
            sub_process.sequence_flows = inner_sequence_flows

            _add_implicit_start_end_events(sub_process)
            bpmn_task = sub_process
        else:
            # fallback to generic task and log state of an unknown activity type
            print(f"Unknown activity type: {activity_type} for id {activity_id}")
            bpmn_task = BPMNTask(id=activity_id, name=name)

        if bpmn_task:
            flow_elements.append(bpmn_task)
            task_map[activity_id] = bpmn_task

    ### second loop: getting sequence_flows
    for activity_id, activity_data in activities.items():
        source_task = task_map.get(activity_id)

        if not source_task:
            # this shouldn't happen, but just in case
            print(f"Source task for flow {activity_id} not found")
            continue

        goto_data = activity_data.get("goto")
        target_tasks: list[tuple[BPMNFlowElement, str | None]] = []  # >1 if conditional, only 1 if not
        if isinstance(goto_data, str):  # direct flow
            target_tasks.append((task_map.get(goto_data), None))
        elif isinstance(goto_data, list):  # conditional flow
            if not isinstance(source_task, BPMNExclusiveGateway):
                print(f"Warning: found 'goto' list for non-exclusive gateway {source_task.id}")
                continue
            for condition_item in goto_data:
                condition_if = condition_item.get("if")
                condition_target = condition_item.get("then")
                if condition_if and condition_target:
                    target_tasks.append((task_map.get(condition_target), condition_if))

        for target_task, condition in target_tasks:
            flow_id = _generate_sequence_flow_id()
            flow_name = None
            if condition and len(condition) < 50:  # use condition as name if short enough
                flow_name = condition
            sequence_flow = BPMNSequenceFlow(
                id=flow_id,
                source_ref=source_task.id,
                target_ref=target_task.id,
                name=flow_name,
                condition_expression=condition
            )
            sequence_flows.append(sequence_flow)
            source_task.add_outgoing_flow(flow_id)
            target_task.add_incoming_flow(flow_id)

    return flow_elements, sequence_flows

def parse_playbook_to_bpmn_representation(playbook_yaml: dict) -> BPMNProcess:
    process_id_from_yaml = playbook_yaml.get("process", "DefaultPlaybookProcess")

    bpmn_process = BPMNProcess(id=process_id_from_yaml, name=process_id_from_yaml)

    # reset counter to 0 for each processed playbook
    global _flow_id_counter, _start_event_id_counter, _end_event_id_counter, _timer_event_definition_id_counter
    _flow_id_counter = 0
    _start_event_id_counter = 0
    _end_event_id_counter = 0
    _timer_event_definition_id_counter = 0

    top_level_activities = playbook_yaml.get("activities", {})
    flow_elements, sequence_flows = _parse_activities_recursive(
        activities=top_level_activities
    )

    for flow_element in flow_elements:
        bpmn_process.add_flow_element(element=flow_element)

    for sequence_flow in sequence_flows:
        bpmn_process.add_sequence_flow(element=sequence_flow)

    _add_implicit_start_end_events(bpmn_process_object=bpmn_process)

    return bpmn_process
