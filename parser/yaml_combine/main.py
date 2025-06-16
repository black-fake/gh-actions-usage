import os
import sys

import yaml
import logging

from yaml2bpmn_converter import yaml_parser, xml_generator

logger = logging.getLogger(__name__)

START_DIRECTORY = "../../playbooks" # Directory to start searching playbooks
OUTPUT_DIRECTORY = "./output"       # Output directory, where combined files will be stored
BPMN_OUTPUT_DIRECTORY = "./output/bpmn"

activity_counter: int = 0 # Global variable for counting activities (more infos see "add_counter_to_activities" function)

def list_directory(dir:str):
    '''
    Lists all directories and files within on directory
    The files and directories are split into two separate lists

    :param dir: expects an existing directory
    :return: (list,list)
        dirs: Subdirctorys within the defined directory
        files: files within the defined directory
    '''
    dirs = []
    files = []
    for entry in os.listdir(dir):
        full_path = os.path.join(dir, entry)
        if os.path.isdir(full_path):
            dirs.append(full_path)
        if os.path.isfile(full_path):
            files.append(full_path)
    return dirs, files

def get_activities(obj:dict):
    '''
    extracts all activities on the highest level of a data structure
    in case the dict has a key "activities"

    :param obj: complex data structure which has at least a dict in the highest level of the data structure
    :return: List of all direct members of the activity Key
    '''
    if not "activities" in obj.keys():
        return []
    return [x for x in obj["activities"].keys()]

def get_activitie_object_type(activity_obj):
    '''
    Identifies the general type, of an activity element

    :param activity_obj:
    :return: one of the following strings (task, gateway, event, subprocess) depending on what kind of BPMN Object the activity represents
        or an empty string if no type could be identified
    '''
    if not "type" in activity_obj.keys():
        return ""
    type = activity_obj["type"]
    if type in ["human", "manual", "busin", "call", "send", "receive", "script", "serv", "task"]:
        return "task"
    if type in ["xgw", "pgw", "igw"]:
        return "gateway"
    if type in ["insthrow", "inscatch", "inmthrow", "inmcatch", "intimer", "inescal"]:
        return "event"
    if type in ["sub"]:
        return "subprocess"

    return ""

def add_counter_to_activities(obj):
    '''
    This functions replaces the keys of all activities within data structure a by a version with an _<counting_number> at the end of the name
    e.g. original key name: "quarantine_device" new key name "quarantine_device_42"
    So each of the activites has a unique number within the final document
    This is replacement is required to eliminate duplicates in the resulting data structure,
    because BPMNator is not able to handle duplicate activity names

    :param obj: a complex data structure which is a dict on its toplevel. The function will actively modify the data in this data structure.
    :return: None
    '''
    global activity_counter

    assigned_numbers={}
    # Step 1: Rename all activities and its child activities
    for activity in get_activities(obj):
        # Call a method to add a number to all inner activities of this activity object
        add_counter_to_activities(obj["activities"][activity])
        # Replace the key of the activity by a key with an added activity_counter The replacement
        # is being realized by creating a new node in the dict as a copy of the old one just with
        # the new key name This new node is beeing attached at the bottom of the dict. This
        # replacement only works, because the for loop iterates over the activities from top to
        # bottom. so the sorting of the data remains correct after replacing all nodes in the
        # activity node.
        activity_counter += 1
        assigned_numbers[activity] = activity_counter
        obj["activities"][activity + "_" + str(activity_counter)] = obj["activities"][activity]
        del obj["activities"][activity]

    # Step 2: adjust naming for goto steps in gateway and send
    for activity in get_activities(obj):
        if "gateway" == get_activitie_object_type(obj["activities"][activity]) and \
           "goto" in obj["activities"][activity].keys():
            for goto_element in obj["activities"][activity]["goto"]:
                # Für exclusive gateways
                if isinstance(goto_element, dict) and "then" in goto_element.keys():
                    goto_element["then"] = goto_element["then"] + "_" + str(assigned_numbers[goto_element["then"]])
                # Für parallel gateway (TODO: Noch nicht testbar wegen fehlendem vorkommen in PBs)
                if isinstance(goto_element, str):
                    obj["activities"][activity]["goto"].append(goto_element+"_"+str(assigned_numbers[goto_element]))
                    obj["activities"][activity]["goto"].remove(goto_element)

        if (
            "task" == get_activitie_object_type(obj["activities"][activity]) or
            "event" == get_activitie_object_type(obj["activities"][activity])
            ) and "goto" in obj["activities"][activity].keys():
            if isinstance(obj["activities"][activity]["goto"], str):
                obj["activities"][activity]["goto"] = obj["activities"][activity]["goto"] + "_" +str(assigned_numbers[obj["activities"][activity]["goto"]])

def load_yaml_file(yaml_file):
    '''
    save loading of a yaml file and converting it into a usable datastructure
    :param yaml_file: a valid yaml file
    :return: data structure of dicts and lists representing the yaml content
    '''
    with open(yaml_file) as f:
        try:
            yaml_data = yaml.safe_load(f)
            return yaml_data
        except yaml.YAMLError as exc:
            logger.error("[-]%s", exc)
            sys.exit(-1)

def process_playbook(playbook_obj, playbook_phase):
    '''
    Iterates over the playbook data structure and inserts module data where it is reverenced in the main playbook file
    The inserted "playbook_obj" will be modified in this function.
    This function uses recursion to ensure a proper parsing of unclear depth of subprocess nesting
    It calls itself again, if it finds a subprocess in the activities of the provided dataset
    and makes the function call with the data structure of the subprocess as argument.
    The recursion ends if an activity has only tasks and no more subprocesses

    :param playbook_obj: data structure representing the yaml content of the playbook or fracation of it
    :param playbook_phase: current phase of the play book. Needet referencing the possible module locations
    :return: None
    '''
    # Iterate over all activities in the provided data structure
    for activity in get_activities(playbook_obj):
        activity_obj = playbook_obj["activities"][activity]

        # if a found activity is a task try to replace it with the corresponding module
        if "task" == get_activitie_object_type(activity_obj):
                logger.debug("[+] Task %s found", activity_obj)
                # If the element is a task insert an activity key with the content of the module activity
                possible_file_locations = [
                    os.path.join(playbook_phase, "modules"),
                    "../../playbooks/05_documentation",
                    "../../playbooks/05_documentation/modules"
                ]  # Modules can be placed at one of this locations

                # Search the fitting module file within this loop
                for possible_file_location in possible_file_locations:
                    file_to_load = os.path.join(possible_file_location, activity + ".yml")
                    logger.debug("[*] Searching module %s at location %s", activity,
                                 file_to_load)
                    if os.path.isfile(file_to_load):
                        logger.debug("[+] Module found at location %s ", file_to_load)
                        # Module file has been found now try to insert the module
                        try:
                            module_yaml = load_yaml_file(file_to_load)
                            activity_obj["activities"] = module_yaml["activities"]
                            activity_obj["type"] = "sub"  # by inserting the module the task converts into a subprocess
                            break  # Module found, no search for further modules needed
                        except KeyError as ex:
                            logger.error("[-] Unable to convert file %s", possible_file_location)

        # if the found activity is a subprocess call this funktion again for this subprocess
        # because each subprocess can/will contain further tasks which needs to be replaced with the
        # corresponding module
        elif "subprocess" == get_activitie_object_type(activity_obj):
            process_playbook(activity_obj, playbook_phase)



if __name__ == '__main__':
    '''
    Iterate over all playbooks and create combined files for each playbook phase
    '''

    logging.basicConfig(filename='yaml_combiner.log', level=logging.DEBUG)
    # Create Playbook Output directory if not exist
    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)

    # Specific folders in the Playbook directory, which shall not be processed like normal Playbook directories
    specific_folders = ["/files", "/05_documentation", "additional_fields"]

    # Iterate over possible playbook directorys and convert the splitted files into one big Playbook
    playbook_dirs, playbook_files = list_directory(START_DIRECTORY)
    for playbook_dir in playbook_dirs:

        if any(playbook_dir.endswith(x) for x in specific_folders):
            # fields directory is not a playbook directory
            continue

        # Temp restriction for malware playbook only
        # TODO: die Folgenden beiden Zeilen müssen enfernt werden, sobald alle Playbooks übersetzt werden können
        if not playbook_dir.endswith("/malware_new"):
            continue

        playbook_phases = list_directory(playbook_dir)[0]
        for playbook_phase in playbook_phases:
            playbook_related_folder, playbook_files = list_directory(playbook_phase)

            logger.info("[+] Processing playbook at following location: \"%s\"",  playbook_phase)
            for playbook_file in playbook_files:
                # Convert yaml file into data structure
                playbook_yaml = load_yaml_file(playbook_file)
                # Process playbook and insert modules in data structure where referenced
                process_playbook(playbook_yaml, playbook_phase)
                # add a rolling number to each activity name to evade duplicates
                add_counter_to_activities(playbook_yaml)
                # Convert the modified object back into yaml
                # The flags default_flow_style=False, sort_keys=False are necessary in this case.
                # They enforce that the orientation of the keys in the object will not be reorderd
                # The ordering is important, because the BPMNator would not process it otherwise

                # If you want to have files for the yaml output, uncomment the following two lines
                #
                # with open(os.path.join(OUTPUT_DIRECTORY, playbook_yaml["process"]+".yml"), "w") as f:
                #     f.write(yaml.dump(playbook_yaml, default_flow_style=False, sort_keys=False))
                # logger.info("[+] Created combined file: \"%s\"", playbook_yaml["process"]+".yml")

                # Convert the modified object into BPMN
                bpmn_yaml = yaml_parser.parse_playbook_to_bpmn_representation(playbook_yaml)
                bpmn_xml = xml_generator.generate_bpmn_xml(bpmn_yaml)
                if not os.path.exists(BPMN_OUTPUT_DIRECTORY):
                    os.makedirs(BPMN_OUTPUT_DIRECTORY)
                with open(os.path.join(BPMN_OUTPUT_DIRECTORY, playbook_yaml["process"]+".bpmn"), "w") as f:
                    f.write(bpmn_xml)
                logger.info("[+] Created BPMN file: \"%s\"", playbook_yaml["process"]+".bpmn")
                print("created BPMN File: %s", playbook_yaml["process"]+".bpmn")
