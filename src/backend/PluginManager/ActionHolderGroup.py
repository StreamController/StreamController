from copy import deepcopy

from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport


class ActionHolderGroup:
    def __init__(self, group_name: str, action_holders: list[ActionHolder], hide_on_group_support: bool = False, group_support: dict[Input, ActionHolder] = {
        Input.Key: ActionInputSupport.UNTESTED,
        Input.Dial: ActionInputSupport.UNTESTED,
        Input.Touchscreen: ActionInputSupport.UNTESTED,
    }):
        """
        Args:
            group_name: The name of the group.
            action_holders: All Action Holders contained in this group.
            hide_on_group_support: Hides the Group in the Action Chooser when the Group is not Supported.
            group_support: The Support types for the various Input Types.
        """
        self._group_name: str = group_name
        self._action_holders: set[ActionHolder] = set(action_holders)
        self._group_support = deepcopy(group_support)
        self._hide_on_group_support: bool = hide_on_group_support

    def add_action_holder(self, action_holder: ActionHolder):
            self._action_holders.add(action_holder)

    def add_action_holders(self, action_holders: list[ActionHolder]):
        self._action_holders.update(action_holders)

    def remove_action_holder(self, action_holder: ActionHolder):
        self._action_holders.remove(action_holder)

    def remove_action_holders(self, action_holders: list[ActionHolder]):
        self._action_holders.difference_update(action_holders)

    def get_group_name(self):
        return self._group_name

    def get_action_holders(self):
        return self._action_holders

    def get_group_support(self):
        return self._group_support

    def get_hide_on_group_support(self):
        return self._hide_on_group_support

    def get_input_compatibility(self, identifier: InputIdentifier) -> ActionInputSupport:
        return self._group_support.get(type(identifier), ActionInputSupport.UNSUPPORTED)