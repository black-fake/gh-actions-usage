import xml.etree.ElementTree as ET
from .bpmn_object_models import *

def _indent_xml(elem, level=0):
    indent = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for sub_elem in elem:
            _indent_xml(sub_elem, level+1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = indent
    elif level and (not elem.tail or not elem.tail.strip()):
        elem.tail = indent

def _build_xml_for_container(
        container_object: BPMNProcess | BPMNSubProcess,
        parent_xml_element: ET.Element,
        definition_attributes: dict
):
    for task_or_event in container_object.flow_elements:
        attributes = {
            "id": task_or_event.id,
            "name": task_or_event.name
        }
        task_or_event_xml_element: ET.Element = None
        element_tag: str = ""

        # handle different task/event types
        if isinstance(task_or_event, BPMNStartEvent): element_tag = "startEvent"
        elif isinstance(task_or_event, BPMNEndEvent): element_tag = "endEvent"
        elif isinstance(task_or_event, BPMNUserTask): element_tag = "userTask"
        elif isinstance(task_or_event, BPMNSendTask): element_tag = "sendTask"
        elif isinstance(task_or_event, BPMNManualTask): element_tag = "manualTask"
        elif isinstance(task_or_event, BPMNExclusiveGateway): element_tag = "exclusiveGateway"
        elif isinstance(task_or_event, BPMNIntimerEvent):
            element_tag = "intermediateCatchEvent"
            # intimer: needs additional timerEventDefinition child item
            task_or_event_xml_element = ET.SubElement(parent_xml_element, f"{{{definition_attributes['xmlns:bpmn']}}}bpmn:{element_tag}", attributes)
            timer_event_definition_attributes = {
                "id": task_or_event.timer_event_definition_id
            }
            ET.SubElement(task_or_event_xml_element, f"{{{definition_attributes['xmlns:bpmn']}}}bpmn:timerEventDefinition", timer_event_definition_attributes)
        elif isinstance(task_or_event, BPMNSubProcess):
            element_tag = "subProcess"
            # subprocess: create element, then recurse
            task_or_event_xml_element = ET.SubElement(parent_xml_element, f"{{{definition_attributes['xmlns:bpmn']}}}bpmn:{element_tag}", attributes)
            _build_xml_for_container(task_or_event, task_or_event_xml_element, definition_attributes)
        elif isinstance(task_or_event, BPMNTask): element_tag = "task"

        # create XML element for task/event
        if element_tag and not (isinstance(task_or_event, BPMNSubProcess) or isinstance(task_or_event, BPMNIntimerEvent)):
            task_or_event_xml_element = ET.SubElement(parent_xml_element, f"{{{definition_attributes['xmlns:bpmn']}}}bpmn:{element_tag}", attributes)

        # add incoming/outgoing flow references to task/event
        if task_or_event_xml_element is not None and isinstance(task_or_event, BPMNFlowElement):
            for flow_id in task_or_event.incoming_flows:
                ET.SubElement(task_or_event_xml_element, f"{{{definition_attributes['xmlns:bpmn']}}}bpmn:incoming").text = flow_id
            for flow_id in task_or_event.outgoing_flows:
                ET.SubElement(task_or_event_xml_element, f"{{{definition_attributes['xmlns:bpmn']}}}bpmn:outgoing").text = flow_id
    # add sequence flows
    for sequence_flow in container_object.sequence_flows:
        attributes = {
            "id": sequence_flow.id,
            "name": sequence_flow.name,
            "sourceRef": sequence_flow.source_ref,
            "targetRef": sequence_flow.target_ref
        }

        sequence_flow_xml_element = ET.SubElement(parent_xml_element, f"{{{definition_attributes['xmlns:bpmn']}}}bpmn:sequenceFlow", attributes)

        if sequence_flow.condition_expression:
            condition_expression_attributes = {
                f"{{{definition_attributes['xmlns:xsi']}}}type": "tFormalExpression"
            }
            condition_expression_xml_element = ET.SubElement(sequence_flow_xml_element, f"{{{definition_attributes['xmlns:bpmn']}}}bpmn:conditionExpression", condition_expression_attributes)
            condition_expression_xml_element.text = sequence_flow.condition_expression

def generate_bpmn_xml(bpmn_process: BPMNProcess):
    # bpmn
    bpmn_namespace = "http://www.omg.org/spec/BPMN/20100524/MODEL"
    # bpmn diagram interchange
    bpmn_di_namespace = "http://www.omg.org/spec/BPMN/20100524/DI"
    # diagram common types
    dc_namespace = "http://www.omg.org/spec/DD/20100524/DC"
    # diagram interchange
    di_namespace = "http://www.omg.org/spec/DD/20100524/DI"
    # xml schema instance
    xsi_namespace = "http://www.w3.org/2001/XMLSchema-instance"
    # target namespace (bpmn)
    target_namespace = "http://bpmn.io/schema/bpmn"

    ET.register_namespace("", bpmn_namespace)
    ET.register_namespace("xsi", xsi_namespace)

    # <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" targetNamespace="http://bpmn.io/schema/bpmn">

    definition_attributes = {
        "xmlns:bpmn": bpmn_namespace,
        "xmlns:bpmndi": bpmn_di_namespace,
        "xmlns:dc": dc_namespace,
        "xmlns:di": di_namespace,
        "xmlns:xsi": xsi_namespace,
        "targetNamespace": target_namespace
    }

    definitions_xml_element = ET.Element(f"{{{bpmn_namespace}}}bpmn:definitions", definition_attributes)

    #   <bpmn:process id="Contain_malware" name="contain_malware" isExecutable="true">

    process_attributes = {
        "id": bpmn_process.id,
        "name": bpmn_process.name,
        "isExecutable": str(bpmn_process.is_executable).lower()
    }

    process_xml_element = ET.SubElement(definitions_xml_element, f"{{{bpmn_namespace}}}bpmn:process", process_attributes)

    _build_xml_for_container(bpmn_process, process_xml_element, definition_attributes)

    # pretty print the xml
    try:
        ET.indent(definitions_xml_element, space="\t")
    except AttributeError:
        _indent_xml(definitions_xml_element) # Fallback for older python versions

    return ET.tostring(definitions_xml_element, encoding="unicode", xml_declaration=True)