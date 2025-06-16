# --- BPMN Model Classes

class BPMNElement:  # -> FlowElement, SequenceFlow, Process
    """Base Class for all BPMN Elements"""
    def __init__(self, id: str, name: str = None):
        self.id = id
        self.name = name if name else id

class BPMNFlowElement(BPMNElement):  # -> Task, Event
    """Base Class for elements that flows can connect"""
    def __init__(self, id: str, name: str = None):
        super().__init__(id, name)
        self.incoming_flows: list[str] = [] # <- maybe change type to BPMNSequenceFlow
        self.outgoing_flows: list[str] = [] # <- maybe change type to BPMNSequenceFlow

    def add_incoming_flow(self, flow_ref: str):
        if flow_ref not in self.incoming_flows:
            self.incoming_flows.append(flow_ref)

    def add_outgoing_flow(self, flow_ref: str):
        if flow_ref not in self.outgoing_flows:
            self.outgoing_flows.append(flow_ref)

class BPMNTask(BPMNFlowElement):  # -> UserTask, SendTask, ManualTask, Gateway, Subprocess
    """Base class for Tasks and Subprocesses"""
    pass

class BPMNUserTask(BPMNTask):
    """Class for User Tasks (human with software assistance)"""
    pass

class BPMNSendTask(BPMNTask):
    """Class for Send Tasks"""
    pass

class BPMNManualTask(BPMNTask):
    """Class for Manual Tasks (human without software assistance)"""
    pass

class BPMNIntimerEvent(BPMNTask):
    """Intermediate Catch Event"""
    def __init__(self, id: str, name: str = None, timer_event_definition_id: str = None):
        super().__init__(id, name)
        self.timer_event_definition_id = timer_event_definition_id

class BPMNExclusiveGateway(BPMNTask):
    """Class for Exclusive Gateways"""
    pass

class BPMNEvent(BPMNFlowElement):  # -> StartEvent, EndEvent
    """Base Class for Events (start, end)"""

class BPMNStartEvent(BPMNEvent):
    """Start Event"""
    pass

class BPMNEndEvent(BPMNEvent):
    """End Event"""
    pass

class BPMNSequenceFlow(BPMNElement):
    """Class for Sequence Flows"""
    def __init__(self, id: str, source_ref: str, target_ref: str, name: str = None, condition_expression: str = None):
        super().__init__(id, name)
        self.source_ref = source_ref
        self.target_ref = target_ref
        self.condition_expression = condition_expression # for flows from exclusive gateways

class BPMNProcessTemplateMixin(BPMNElement):
    """Base Class to define methods of Processes and Subprocesses"""

    def __init__(self, id: str, name: str = None):
        super().__init__(id, name)
        self.start_event: BPMNStartEvent = None
        self.end_events: list[BPMNEndEvent] = []
        self.flow_elements: list[BPMNFlowElement] = []
        self.sequence_flows: list[BPMNSequenceFlow] = []

    def add_flow_element(self, element: BPMNFlowElement):
        if element not in self.flow_elements:
            self.flow_elements.append(element)

    def add_sequence_flow(self, flow: BPMNSequenceFlow):
        if flow not in self.sequence_flows:
            self.sequence_flows.append(flow)

    def add_end_event(self, end_event: BPMNEndEvent):
        if end_event not in self.end_events:
            self.end_events.append(end_event)

    def set_start_event(self, start_event: BPMNStartEvent):
        self.start_event = start_event

    def clean_start_end_events(self):
        self.start_event = None
        self.end_events = []

class BPMNProcess(BPMNProcessTemplateMixin):
    """Class for main Process"""
    def __init__(self, id: str, name: str = None, is_executable: bool = True):
        BPMNProcessTemplateMixin.__init__(self, id, name)
        self.is_executable = is_executable

class BPMNSubProcess(BPMNTask, BPMNProcessTemplateMixin):
    """Class for subprocesses"""
    pass