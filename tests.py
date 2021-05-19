import unittest
import json

import node_tools as nt
from abtest import SwitchCategory
from rapidpro_abtest_creator import RapidProABTestCreator, apply_editops_to_node
from testing_tools import Context
from testing_tools import traverse_flow, find_final_destination
from sheets import abtest_from_csv, floweditsheet_from_csv
from sheets import CSVMasterSheetParser
from contact_group import ContactGroup
from operations import *
import logging
import copy

logging.basicConfig(filename='tests.log', level=logging.WARNING, filemode='w')

test_node = {
    "uuid": "aa0028ce-6f67-4313-bdc1-c2dd249a227d",
    "actions": [
        {
            "attachments": [],
            "text": "Good morning!",
            "type": "send_msg",
            "all_urns": False,
            "quick_replies": ["Yes", "Maybe", "No"],
            "uuid": "72d69a5d-ba85-4b94-81a1-e550ee43758d"
        }
    ],
    "exits": [
        {
            "uuid": "f90de082-5409-4ce7-8e40-d649458215d2",
            "destination_uuid": "3f6c8241-5d52-4b5b-8ba5-0f8f8cfdc4a0"
        }
    ]
}

test_value_actions_node = {
    "uuid": "aa0028ce-6f67-4313-bdc1-c2dd249a227d",
    "actions": [
        {
            "type": "set_contact_name",
            "uuid": "8eebd020-1af5-431c-b943-aa670fc74da1",
            "name": "Bob Smith"
        },
        {
            "type": "set_contact_language",
            "uuid": "8eebd020-1af5-431c-b943-aa670fc74da2",
            "language": "eng"
        },
        {
            "type": "set_contact_field",
            "uuid": "8eebd020-1af5-431c-b943-aa670fc74da3",
            "field": {
                "key": "variable",
                "name": "Variable"
            },
            "value": "some value"
        },
        {
            "type": "set_run_result",
            "uuid": "8eebd020-1af5-431c-b943-aa670fc74da9",
            "name": "Result Number 1",
            "value": "some result",
            "category": ""
        }
    ],
    "exits": [
        {
            "uuid": "f90de082-5409-4ce7-8e40-d649458215d2",
            "destination_uuid": None
        }
    ]
}

test_node_3actions = {
    "uuid": "aa0028ce-6f67-4313-bdc1-c2dd249a227d",
    "actions": [
        {
            "attachments": [],
            "text": "The first personalizable message.",
            "type": "send_msg",
            "all_urns": False,
            "quick_replies": [],
            "uuid": "72d69a5d-ba85-4b94-81a1-e550ee43758d"
        },
        {
            "attachments": [],
            "text": "Good morning!",
            "templating": {
                "uuid": "32c2ead6-3fa3-4402-8e27-9cc718175c5a",
                "template": {
                    "uuid": "3ce100b7-a734-4b4e-891b-350b1279ade2",
                    "name": "revive_issue"
                },
                "variables": [
                    "@contact.name"
                ]
            },
            "type": "send_msg",
            "all_urns": False,
            "quick_replies": [],
            "uuid": "72d69a5d-ba85-4b94-81a1-e550ee43758d"
        },
        {
            "attachments": [],
            "text": "Good morning!",
            "type": "send_msg",
            "all_urns": False,
            "quick_replies": [],
            "uuid": "72d69a5d-ba85-4b94-81a1-e550ee43758d"
        }
    ],
    "exits": [
        {
            "uuid": "f90de082-5409-4ce7-8e40-d649458215d2",
            "destination_uuid": "3f6c8241-5d52-4b5b-8ba5-0f8f8cfdc4a0"
        }
    ]
}

class TestNodeTools(unittest.TestCase):
    def setUp(self):
        abtest1 = abtest_from_csv("testdata/Test1_Personalization.csv")
        abtest2 = abtest_from_csv("testdata/Test2_Some1337.csv")
        self.abtests = [abtest1, abtest2]
        self.floweditsheet = floweditsheet_from_csv("testdata/FlowEdit1_Gender.csv")

    def test_get_group_switch_node(self):
        test_op = self.abtests[0].edit_op(1)
        switch = nt.get_switch_node(test_op, ["dest1uuid", "dest2uuid", "dest2uuid"])
        flow = {"nodes" : [switch]}
        dest1 = find_final_destination(flow, switch, Context([self.abtests[0].groupA().name]))
        dest2 = find_final_destination(flow, switch, Context([self.abtests[0].groupB().name]))
        dest3 = find_final_destination(flow, switch, Context())
        self.assertEqual(dest1, "dest1uuid")
        self.assertEqual(dest2, "dest2uuid")
        self.assertEqual(dest3, "dest2uuid")
        # print(json.dumps(switch, indent=4))

    def test_get_switch_node(self):
        test_op = self.floweditsheet.edit_op(0)
        switch = nt.get_switch_node(test_op, ["dest1uuid", "dest2uuid", "dest3uuid"])
        flow = {"nodes" : [switch]}
        dest1 = find_final_destination(flow, switch, Context(variables={"@fields.gender" : "man"}))
        dest2 = find_final_destination(flow, switch, Context(variables={"@fields.gender" : "woman"}))
        dest3 = find_final_destination(flow, switch, Context(variables={"@fields.gender" : "something"}))
        dest4 = find_final_destination(flow, switch, Context())
        self.assertEqual(dest1, "dest1uuid")
        self.assertEqual(dest2, "dest2uuid")
        self.assertEqual(dest3, "dest3uuid")
        self.assertEqual(dest4, "dest3uuid")
        # print(json.dumps(switch, indent=4))

    def test_get_assign_to_group_gadget(self):
        gadget = nt.get_assign_to_group_gadget("GAname", "GAuuid", "GBname", "BGuuid", "destuuid")
        flow = {"nodes" : gadget}
        context1 = Context(random_choices=[0])
        find_final_destination(flow, gadget[0], context1)
        self.assertEqual(len(context1.group_names), 1)
        self.assertEqual(context1.group_names[0], "GAname")
        context2 = Context(random_choices=[1])
        find_final_destination(flow, gadget[0], context2)
        self.assertEqual(len(context2.group_names), 1)
        self.assertEqual(context2.group_names[0], "GBname")
        # print(json.dumps(gadget, indent=4))


class TestOperations(unittest.TestCase):
    def setUp(self):
        abtest1 = abtest_from_csv("testdata/Test1_Personalization.csv")
        abtest2 = abtest_from_csv("testdata/Test2_Some1337.csv")
        self.abtests = [abtest1, abtest2]
        # Same as test_node, but with exit pointing to None.
        self.test_node_x = copy.deepcopy(test_node)
        self.test_node_x["exits"][0]["destination_uuid"] = None

    def test_apply_replace_bit_of_text(self):
        edit_op = self.abtests[1].edit_op(0)
        flow_snippet = edit_op._get_flow_snippet(self.test_node_x)
        self.assertEqual(len(flow_snippet.node_variations()), 2)
        self.assertEqual(flow_snippet.node_variations()[0], self.test_node_x)  # First node should be original

        # Turn snippet into complete flow and simulate it.
        flow = {"nodes" : flow_snippet.nodes()}
        groupsA = [self.abtests[1].groupA().name]
        msgs1 = traverse_flow(flow, Context(groupsA))
        self.assertEqual(msgs1, [('send_msg', 'Good morning!')])
        groupsB = [self.abtests[1].groupB().name]
        msgs2 = traverse_flow(flow, Context(groupsB))
        self.assertEqual(msgs2, [('send_msg', 'g00d m0rn1ng!')])
        msgs3 = traverse_flow(flow, Context())
        self.assertEqual(msgs3, [('send_msg', 'Good morning!')])

    def test_apply_replace_quick_replies(self):
        row = ['replace_quick_replies', '', 0, 'Good morning!', 'Yes;No', '', 'Yeah;Nay']
        edit_op = FlowEditOp.create_edit_op(*row, "debug_str")
        self.assertEqual(type(edit_op), ReplaceQuickReplyFlowEditOp)
        input_node = copy.deepcopy(test_node)
        flow_snippet = edit_op._get_flow_snippet(input_node)
        self.assertEqual(len(flow_snippet.node_variations()), 1)
        quick_replies = flow_snippet.node_variations()[0]["actions"][0]["quick_replies"]
        quick_replies_exp = ['Yeah', 'Maybe', 'Nay']
        self.assertEqual(quick_replies, quick_replies_exp)

    def test_apply_replace_saved_value_1(self):
        row = ['replace_saved_value', '', 0, '@fields.variable', 'some value', '@fields.flag', 'some value']
        edit_op = FlowEditOp.create_edit_op(*row, "debug_str", has_node_for_other_category=True)
        edit_op.add_category(SwitchCategory("Cat1", "has_text", "", 'new value'))
        self.assertEqual(type(edit_op), ReplaceSavedValueFlowEditOp)

        input_node = copy.deepcopy(test_value_actions_node)
        action_index = edit_op._matching_save_value_action_id(input_node)
        self.assertEqual(action_index, 2)
        flow_snippet = edit_op._get_flow_snippet(input_node)
        self.assertEqual(len(flow_snippet.node_variations()), 2)
        self.assertEqual(flow_snippet.node_variations()[0]["actions"][action_index]["value"], "new value")
        self.assertEqual(flow_snippet.node_variations()[1]["actions"][action_index]["value"], "some value")

    def test_apply_replace_saved_value_2(self):
        row = ['replace_saved_value', '', 0, '@contact.name', 'Bob Smith', '@fields.flag', 'Bobby']
        edit_op = FlowEditOp.create_edit_op(*row, "debug_str", has_node_for_other_category=True)
        edit_op.add_category(SwitchCategory("Cat1", "has_text", "", 'Steve'))
        self.assertEqual(type(edit_op), ReplaceSavedValueFlowEditOp)

        input_node = copy.deepcopy(test_value_actions_node)
        action_index = edit_op._matching_save_value_action_id(input_node)
        self.assertEqual(action_index, 0)
        flow_snippet = edit_op._get_flow_snippet(input_node)
        self.assertEqual(len(flow_snippet.node_variations()), 2)
        self.assertEqual(flow_snippet.node_variations()[0]["actions"][action_index]["name"], "Steve")
        self.assertEqual(flow_snippet.node_variations()[1]["actions"][action_index]["name"], "Bobby")

    def test_apply_replace_saved_value_3(self):
        row = ['replace_saved_value', '', 0, '@contact.language', 'eng', '@fields.flag', 'eng']
        edit_op = FlowEditOp.create_edit_op(*row, "debug_str", has_node_for_other_category=False)
        edit_op.add_category(SwitchCategory("Cat1", "has_text", "", 'spa'))  # Ignored
        edit_op.add_category(SwitchCategory("Cat2", "has_text", "", 'fin'))
        self.assertEqual(type(edit_op), ReplaceSavedValueFlowEditOp)

        input_node = copy.deepcopy(test_value_actions_node)
        action_index = edit_op._matching_save_value_action_id(input_node)
        self.assertEqual(action_index, 1)
        flow_snippet = edit_op._get_flow_snippet(input_node)
        self.assertEqual(len(flow_snippet.node_variations()), 2)
        self.assertEqual(flow_snippet.node_variations()[0]["actions"][action_index]["language"], "eng")
        self.assertEqual(flow_snippet.node_variations()[1]["actions"][action_index]["language"], "fin")

    def test_apply_replace_saved_value_4(self):
        row = ['replace_saved_value', '', 0, '@results.result_number_1', 'some result', '@fields.flag', '123Default']
        edit_op = FlowEditOp.create_edit_op(*row, "debug_str", has_node_for_other_category=True)
        edit_op.add_category(SwitchCategory("Cat1", "has_text", "", 'Cat1999'))
        edit_op.add_category(SwitchCategory("Cat2", "has_text", "", 'Cat2999'))
        self.assertEqual(type(edit_op), ReplaceSavedValueFlowEditOp)

        input_node = copy.deepcopy(test_value_actions_node)
        action_index = edit_op._matching_save_value_action_id(input_node)
        self.assertEqual(action_index, 3)
        flow_snippet = edit_op._get_flow_snippet(input_node)
        self.assertEqual(len(flow_snippet.node_variations()), 3)
        self.assertEqual(flow_snippet.node_variations()[0]["actions"][action_index]["value"], "Cat1999")
        self.assertEqual(flow_snippet.node_variations()[1]["actions"][action_index]["value"], "Cat2999")
        self.assertEqual(flow_snippet.node_variations()[2]["actions"][action_index]["value"], "123Default")

    def test_assign_to_group_before_save_value_node(self):
        row = ['assign_to_group_before_save_value_node', '', 0, '@fields.variable', 'some value', '', '']
        edit_op = FlowEditOp.create_edit_op(*row, "debug_str", has_node_for_other_category=False)
        edit_op.add_category(SwitchCategory("CatA", "has_group", ["", "GroupA"], ""))
        edit_op.add_category(SwitchCategory("CatB", "has_group", ["", "GroupB"], ""))

        input_node = copy.deepcopy(test_value_actions_node)
        flow_snippet = edit_op._get_flow_snippet(input_node)
        self.assertEqual(len(flow_snippet.node_variations()), 1)
        self.assertEqual(flow_snippet.node_variations()[0], test_value_actions_node)

        # Turn snippet into complete flow and simulate it.
        flow = {"nodes" : flow_snippet.nodes()}
        exp_common = [('set_contact_name', 'Bob Smith'), 
                      ('set_contact_language', 'eng'),
                      ('set_contact_field', 'Variable'),
                      ('set_run_result', 'Result Number 1')]
        msgs1 = traverse_flow(flow, Context(["GroupA"]))
        self.assertEqual(msgs1, exp_common)
        msgs2 = traverse_flow(flow, Context(random_choices=[0]))
        self.assertEqual(msgs2, [('add_contact_groups', 'GroupA')] + exp_common)
        msgs3 = traverse_flow(flow, Context(random_choices=[1]))
        self.assertEqual(msgs3, [('add_contact_groups', 'GroupB')] + exp_common)


class TestRapidProABTestCreatorMethods(unittest.TestCase):
    def setUp(self):
        filename = "testdata/Linear_OneNodePerAction.json"
        self.rpx = RapidProABTestCreator(filename)
        abtest1 = abtest_from_csv("testdata/Test1_Personalization.csv")
        abtest2 = abtest_from_csv("testdata/Test2_Some1337.csv")
        self.abtests = [abtest1, abtest2]

    def make_minimal_test_op(self, flow_name, row_id, text_content):
        dummy_group = ContactGroup(None, None)
        dummy_group_pair = (dummy_group, dummy_group)
        dummy_row = ["replace_bit_of_text", flow_name, row_id, text_content, "", "", "", ""]
        return FlowEditOp.create_edit_op(*dummy_row, "Debug_str")

    def test_find_nodes(self):        
        # A valid node in given flow with given text
        nodes1 = self.rpx._find_matching_nodes(self.make_minimal_test_op("ABTesting_Pre", -1, 'Good morning!'))
        self.assertEqual(nodes1, ['aa0028ce-6f67-4313-bdc1-c2dd249a227d'])
        # non-existing node text
        nodes2 = self.rpx._find_matching_nodes(self.make_minimal_test_op("ABTesting_Pre", -1, 'LOL!'))
        self.assertEqual(nodes2, [])
        # non-existing flow name
        nodes3 = self.rpx._find_matching_nodes(self.make_minimal_test_op("Trololo", -1, 'Good morning!'))
        self.assertEqual(nodes3, [])

    def test_generate_node_variations(self):
        test_ops = [
            self.abtests[0].edit_op(1),
            self.abtests[1].edit_op(0),
        ]

        flow = {"nodes" : [copy.deepcopy(test_node)]}
        nodes = apply_editops_to_node(flow, flow["nodes"][0], test_ops)
        self.assertEqual(len(nodes), 4)
        self.assertEqual(nodes[0], test_node)  # First node should be original
        self.assertEqual(nodes[1]["actions"][0]["text"], "g00d m0rn1ng!")
        self.assertEqual(nodes[2]["actions"][0]["text"], "Good morning, Steve!")
        self.assertEqual(nodes[3]["actions"][0]["text"], "g00d m0rn1ng, Steve!")
        destination_uuid = test_node["exits"][0]["destination_uuid"]
        self.assertEqual(nodes[1]["exits"][0]["destination_uuid"], destination_uuid)
        self.assertEqual(nodes[2]["exits"][0]["destination_uuid"], destination_uuid)
        self.assertEqual(nodes[3]["exits"][0]["destination_uuid"], destination_uuid)
        self.assertNotEqual(test_node["uuid"], nodes[1]["uuid"])
        self.assertNotEqual(test_node["actions"][0]["uuid"], nodes[1]["actions"][0]["uuid"])
        self.assertNotEqual(test_node["exits"][0]["uuid"], nodes[1]["exits"][0]["uuid"])
        # print(json.dumps([v.node for v in variations], indent=4))

    def test_generate_node_variations_multiple_actions(self):
        test_ops = [
            self.abtests[0].edit_op(0),
            self.abtests[1].edit_op(0),
        ]

        flow = {"nodes" : [copy.deepcopy(test_node_3actions)]}
        nodes = apply_editops_to_node(flow, flow["nodes"][0], test_ops)
        self.assertEqual(nodes[0], test_node_3actions)  # First node should be original
        self.assertEqual(nodes[1]["actions"][0]["text"], "The first personalizable message.")
        self.assertEqual(nodes[2]["actions"][0]["text"], "The first personalizable message, Steve!")
        self.assertEqual(nodes[3]["actions"][0]["text"], "The first personalizable message, Steve!")
        self.assertEqual(nodes[1]["actions"][1]["text"], "g00d m0rn1ng!")
        self.assertEqual(nodes[2]["actions"][1]["text"], "Good morning!")
        self.assertEqual(nodes[3]["actions"][1]["text"], "g00d m0rn1ng!")
        self.assertEqual(nodes[1]["actions"][2]["text"], "g00d m0rn1ng!")
        self.assertEqual(nodes[2]["actions"][2]["text"], "Good morning!")
        self.assertEqual(nodes[3]["actions"][2]["text"], "g00d m0rn1ng!")
        self.assertNotEqual(test_node_3actions["actions"][0]["uuid"], nodes[1]["actions"][0]["uuid"])
        self.assertNotEqual(test_node_3actions["actions"][1]["uuid"], nodes[1]["actions"][1]["uuid"])
        self.assertNotEqual(test_node_3actions["actions"][2]["uuid"], nodes[1]["actions"][2]["uuid"])
        self.assertNotEqual(test_node_3actions["actions"][1]["templating"]["uuid"], nodes[1]["actions"][1]["templating"]["uuid"])


class TestRapidProABTestCreatorLinear(unittest.TestCase):
    def setUp(self):
        abtest1 = abtest_from_csv("testdata/Test1_Personalization.csv")
        abtest2 = abtest_from_csv("testdata/Test2_Some1337.csv")
        self.abtests = [abtest1, abtest2]

    def test_apply_abtests_linear_onenodeperaction(self):
        filename = "testdata/Linear_OneNodePerAction.json"
        rpx = RapidProABTestCreator(filename)
        rpx.apply_abtests(self.abtests)
        self.evaluate_result(rpx)

    def test_apply_abtests_linear_twoactionspernode(self):
        filename = "testdata/Linear_TwoActionsPerNode.json"
        rpx = RapidProABTestCreator(filename)
        rpx.apply_abtests(self.abtests)
        self.evaluate_result(rpx)

    def test_apply_abtests_linear_nodewith3actions(self):
        filename = "testdata/Linear_NodeWith3Actions.json"
        rpx = RapidProABTestCreator(filename)
        rpx.apply_abtests(self.abtests)
        self.evaluate_result(rpx)

    def test_apply_abtests_linear_onenode4actions(self):
        filename = "testdata/Linear_OneNode4Actions.json"
        rpx = RapidProABTestCreator(filename)
        rpx.apply_abtests(self.abtests)
        self.evaluate_result(rpx)

    def evaluate_result(self, rpx):
        exp1 = [
            ('send_msg', 'The first personalizable message.'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'Good morning!'),
            ('send_msg', 'This is a test.'),
        ]
        exp2 = [
            ('send_msg', 'The first personalizable message.'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'g00d m0rn1ng!'),
            ('send_msg', 'This is a test.'),
        ]
        exp3 = [
            ('send_msg', 'The first personalizable message, Steve!'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'g00d m0rn1ng, Steve!'),
            ('send_msg', 'This is a test.'),
        ]
        exp4 = exp1

        # Traverse the flow with different group memberships and check the sent messages.
        flows = rpx.data_["flows"][0]
        groupsAA = [self.abtests[0].groupA().name, self.abtests[1].groupA().name]
        msgs1 = traverse_flow(flows, Context(groupsAA))
        self.assertEqual(msgs1, exp1)
        groupsAB = [self.abtests[0].groupA().name, self.abtests[1].groupB().name]
        msgs2 = traverse_flow(flows, Context(groupsAB))
        self.assertEqual(msgs2, exp2)
        groupsBB = [self.abtests[0].groupB().name, self.abtests[1].groupB().name]
        msgs3 = traverse_flow(flows, Context(groupsBB))
        self.assertEqual(msgs3, exp3)
        msgs4 = traverse_flow(flows, Context())  # "Other" branch. Should be same as msgs1
        self.assertEqual(msgs4, exp4)


class TestRapidProABTestCreatorBranching(unittest.TestCase):

    def set_up_branching(self, filename):
        self.abtests = [abtest_from_csv(filename)]
        self.groupA_name = self.abtests[0].groupA().name
        self.groupB_name = self.abtests[0].groupB().name
        filename = "testdata/Branching.json"
        rpx = RapidProABTestCreator(filename)
        rpx.apply_abtests(self.abtests)
        self.flows = rpx.data_["flows"][0]

    def test_apply_abtests_1(self):
        self.set_up_branching("testdata/Branching.csv")
        self.apply_abtests_1()

    def test_apply_abtests_2(self):
        self.set_up_branching("testdata/Branching.csv")
        self.apply_abtests_2()

    def test_apply_abtests_3(self):
        self.set_up_branching("testdata/Branching.csv")
        self.apply_abtests_3()

    def test_apply_abtests_4(self):
        self.set_up_branching("testdata/Branching.csv")
        self.apply_abtests_4()

    # These tests use a separate spreadsheet without an
    # assign_to_group column and instead manually inserts
    # assign_to_group operations
    def test_apply_abtests_1_equivalent(self):
        self.set_up_branching("testdata/Branching_equivalent.csv")
        self.apply_abtests_1()

    def test_apply_abtests_2_equivalent(self):
        self.set_up_branching("testdata/Branching_equivalent.csv")
        self.apply_abtests_2()

    def test_apply_abtests_3_equivalent(self):
        self.set_up_branching("testdata/Branching_equivalent.csv")
        self.apply_abtests_3()

    def test_apply_abtests_4_equivalent(self):
        self.set_up_branching("testdata/Branching_equivalent.csv")
        self.apply_abtests_4()

    def apply_abtests_1(self):
        exp1 = [
            ('send_msg', 'Text1'),
            ('send_msg', 'Text21'),
            ('send_msg', 'Text3 replaced'),
            ('send_msg', 'Text61'),
            ('send_msg', 'Text61 Again replaced'),
            ('send_msg', 'Text7')
        ]
        groups1 = [self.groupB_name, "Survey Audience"]
        output1 = traverse_flow(self.flows, Context(groups1, ["Good"], []))
        self.assertEqual(output1, exp1)

        # We enforce the same group assignment with the random choice "1"
        exp2 = exp1[:2] + [('add_contact_groups', self.groupB_name)] + exp1[2:]
        groups2 = ["Survey Audience"]
        output2 = traverse_flow(self.flows, Context(groups2, ["Good"], [1]))
        self.assertEqual(output2, exp2)

    def apply_abtests_2(self):
        exp1 = [
            ('send_msg', 'Text1'),
            ('send_msg', 'Text23'),
            ('set_run_result', 'Result 2'),
            ('send_msg', 'Text23 Again replaced'),
            ('add_contact_groups', 'Survey Audience'),
            ('send_msg', 'Text41'),
            ('send_msg', 'Text61'),
            ('send_msg', 'Text61 Again replaced'),
            ('send_msg', 'Text7')
        ]
        groups1 = [self.groupB_name, "Survey Audience"]
        output1 = traverse_flow(self.flows, Context(groups1, ["Something", "Yes"], []))
        self.assertEqual(output1, exp1)

        # We enforce the same testing group assignment with the random choice "1"
        # "Survey Audience" is being added by the choice "Yes"
        exp2 = exp1[:1] + [('add_contact_groups', self.groupB_name)] + exp1[1:]
        groups2 = []
        output2 = traverse_flow(self.flows, Context(groups2, ["Something", "Yes"], [1]))
        self.assertEqual(output2, exp2)

    def apply_abtests_3(self):
        exp1 = [
            ('send_msg', 'Text1'),
            ('send_msg', 'Text22'),
            ('send_email', 'Spam Email'),
            ('add_contact_groups', self.groupA_name),
            ('send_msg', 'Text3'),
            ('send_msg', 'Text62'),
            ('send_msg', 'Text7')
        ]
        groups1 = []
        output1 = traverse_flow(self.flows, Context(groups1, ["Bad"], [0]))
        self.assertEqual(output1, exp1)

    def apply_abtests_4(self):
        exp1 = [
            ('send_msg', 'Text1'),
            ('add_contact_groups', self.groupB_name),
            ('send_msg', 'Text23'),
            ('set_run_result', 'Result 2'),
            ('send_msg', 'Text23 Again replaced'),
            ('send_msg', 'Text42 replaced'),
            ('send_msg', 'Text62 replaced'),
            ('send_msg', 'Text7')
        ]
        groups1 = []
        output1 = traverse_flow(self.flows, Context(groups1, ["otter", "otter"], [1]))
        self.assertEqual(output1, exp1)



class TestRapidProEditsLinear(unittest.TestCase):
    def setUp(self):
        sheet1 = floweditsheet_from_csv("testdata/FlowEdit1_Gender.csv")
        sheet2 = floweditsheet_from_csv("testdata/FlowEdit2_Some1337.csv")
        self.floweditsheets = [sheet1, sheet2]

    def test_apply_abtests_linear_onenodeperaction(self):
        filename = "testdata/Linear_OneNodePerAction.json"
        rpx = RapidProABTestCreator(filename)
        rpx.apply_abtests(self.floweditsheets)
        self.evaluate_result(rpx)

    def test_apply_abtests_linear_onenode4actions(self):
        filename = "testdata/Linear_OneNode4Actions.json"
        rpx = RapidProABTestCreator(filename)
        rpx.apply_abtests(self.floweditsheets)
        self.evaluate_result(rpx)

    def evaluate_result(self, rpx):
        exp1 = [
            ('send_msg', 'The first personalizable message, my person!'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'Good morning, my person!'),
            ('send_msg', 'This is a test.'),
        ]
        exp2 = [
            ('send_msg', 'The first personalizable message, my gal!'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'g00d m0rn1ng, my gal!'),
            ('send_msg', 'This is a test.'),
        ]
        exp3 = [
            ('send_msg', 'The first personalizable message, my dude!'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'Good morning, my dude!'),
            ('send_msg', 'This is a test.'),
        ]
        exp4 = [
            ('send_msg', 'The first personalizable message, my person!'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'g00d m0rn1ng, my person!'),
            ('send_msg', 'This is a test.'),
        ]

        # Traverse the flow with different group memberships and check the sent messages.
        flows = rpx.data_["flows"][0]
        msgs1 = traverse_flow(flows, Context())
        self.assertEqual(msgs1, exp1)
        variables2 = {"@fields.gender" : "woman", "@fields.likes_1337" : "yes"}
        msgs2 = traverse_flow(flows, Context(variables=variables2))
        self.assertEqual(msgs2, exp2)
        variables3 = {"@fields.gender" : "man", "@fields.likes_1337" : ""}
        msgs3 = traverse_flow(flows, Context(variables=variables3))
        self.assertEqual(msgs3, exp3)
        variables4 = {"@fields.gender" : "child", "@fields.likes_1337" : "yossss"}
        msgs4 = traverse_flow(flows, Context(variables=variables4))
        self.assertEqual(msgs4, exp4)


class TestMasterSheet(unittest.TestCase):
    def setUp(self):
        parser = CSVMasterSheetParser("testdata/master_sheet.csv")
        self.floweditsheets = parser.get_flow_edit_sheets()
        self.groupA_name = self.floweditsheets[-1].groupA().name
        self.groupB_name = self.floweditsheets[-1].groupB().name

    def test_apply_abtests_linear_onenodeperaction(self):
        filename = "testdata/Linear_OneNodePerAction.json"
        rpx = RapidProABTestCreator(filename)
        rpx.apply_abtests(self.floweditsheets)
        self.evaluate_result(rpx)

    def test_apply_abtests_linear_onenode4actions(self):
        filename = "testdata/Linear_OneNode4Actions.json"
        rpx = RapidProABTestCreator(filename)
        rpx.apply_abtests(self.floweditsheets)
        self.evaluate_result(rpx)

    def evaluate_result(self, rpx):
        exp1 = [
            ('send_msg', 'The first personalizable message, my person!'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'Good morning, my person!'),
            ('send_msg', 'This is a test.'),
        ]
        exp2 = [
            ('send_msg', 'The first personalizable message, my gal!'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'g00d m0rn1ng, my gal!'),
            ('send_msg', 'This is a test.'),
        ]
        exp3 = [
            ('send_msg', 'The first personalizable message, my dude!'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'Good morning, my dude!'),
            ('send_msg', 'This is a test.'),
        ]
        exp4 = [
            ('send_msg', 'The first personalizable message, my person!'),
            ('send_msg', 'Some generic message.'),
            ('send_msg', 'g00d m0rn1ng, my person!'),
            ('send_msg', 'This is a test.'),
        ]

        # Traverse the flow with different group memberships and check the sent messages.
        flows = rpx.data_["flows"][0]
        msgs1 = traverse_flow(flows, Context([self.groupA_name]))
        self.assertEqual(msgs1, exp1)
        variables2 = {"@fields.gender" : "woman"}
        msgs2 = traverse_flow(flows, Context([self.groupB_name], variables=variables2))
        self.assertEqual(msgs2, exp2)
        variables3 = {"@fields.gender" : "man"}
        msgs3 = traverse_flow(flows, Context([self.groupA_name], variables=variables3))
        self.assertEqual(msgs3, exp3)
        variables4 = {"@fields.gender" : "child"}
        msgs4 = traverse_flow(flows, Context([self.groupB_name], variables=variables4))
        self.assertEqual(msgs4, exp4)


if __name__ == '__main__':
    unittest.main()
