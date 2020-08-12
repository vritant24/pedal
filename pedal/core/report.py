"""
File that holds the the Report class and the global MAIN_REPORT.

Note that you can make other Reports, but that doesn't actually seem to be
useful very often. Usually you want to just rely on the global MAIN_REPORT.
"""

__all__ = ['Report', 'MAIN_REPORT']

from pedal.core.errors import PedalToolNotRegistered, PedalToolAlreadyRegistered
from pedal.core.feedback_category import FeedbackCategory


# TODO: Mechanism for checking whether a piece of feedback is in the report
from pedal.core.formatting import Formatter
from pedal.core.tool import ToolRegistration


class Report:
    """
    A class for storing Feedback generated by Tools, along with any auxiliary
    data that the Tool might want to provide for other tools.

    Attributes:
        submission (:py:class:`~pedal.core.submission.Submission`): The
            contextualized submission information.
        feedback (list[:py:class:`~pedal.core.feedback.Feedback`]): The raw
            feedback generated for this Report so far.
        suppressions (list[tuple[str, str]]): The categories and labels that
            have been suppressed so far.
        hiddens (set[str]): The parts of the final response that should be
            hidden. This can globally hide the 'correct', 'score', etc.
        group (int or str): The label for the current group. Feedback given
            by a Tool will automatically receive the current `group`. This
            is used by the Source tool, for example, in order to group feedback
            by sections.
        group_names (dict[group, str]): A printable, student-facing name for the
            group. When a group needs to be rendered out to the user, this
            will override whatever label was going to be presented instead.
        hooks (dict[str, list[callable]): A dictionary mapping events to
            a list of callable functions. Tools can register functions on
            hooks to have them executed when the event is triggered by another
            tool. For example, the Assertions tool has hooks on the Source tool
            to trigger assertion resolutions before advancing to next sections.
        _tool_data (dict[str, Any]): Maps tool names to their data. The
                                       namespace for a tool can be used to
                                       store whatever they want, but will
                                       probably be in a dictionary itself.
        resolves (list[Any]): The result of having previously called a
            resolver. This allows you to check if a report has previously
            been resolved, or do something with that data.
    """
    #: dict[str, dict]: The
    #: tools registered for this report, available via their names.
    TOOLS = {}

    def __init__(self):
        """
        Creates a new Report instance.
        """
        self._tool_data = {}
        self.feedback = []
        self.ignored_feedback = []
        self.suppressions = {}
        self.suppressed_labels = []
        self.hiddens = set()
        self.groups = []
        self.group = None
        self.group_names = {}
        self.hooks = {}
        self.class_hooks = {}
        self.submission = None
        self.format = Formatter()
        self.result = None
        self.resolves = []

    def clear(self):
        """
        Resets the entire report back to its starting form,
        including deleting any attached submissions, tool data, and feedbacks.
        However, it will not affect class hooks.
        """
        self.feedback.clear()
        self.ignored_feedback.clear()
        self.suppressions.clear()
        self.suppressed_labels.clear()
        self.hiddens.clear()
        self._tool_data.clear()
        self.group = None
        self.group_names.clear()
        self.hooks.clear()
        self.submission = None
        self.result = None
        self.resolves.clear()
        self.format = Formatter()

    def full_clear(self):
        """ This totally resets the report, including any class hooks. """
        self.clear()
        self.class_hooks.clear()

    def contextualize(self, submission):
        """
        Attach the given submission to this report.

        Args:
            submission (:py:class:`pedal.core.submission.Submission`): The
                submission to attach to this report.
        """
        self.submission = submission

    def hide_correctness(self):
        """
        Suppress the RESULT category entirely, so that the report doesn't
        indicate whether or not the submission was correct.
        TODO: Make this just a regular command.
        """
        self.hiddens.add('correct')
        self.hiddens.add('score')

    def add_feedback(self, feedback):
        """
        Attaches the given feedback object to this report.

        Args:
            feedback (:py:class:`~pedal.core.feedback.Feedback`): The feedback
                object to attach.

        Returns:
            :py:class:`~pedal.core.feedback.Feedback`: The attached feedback.
        """
        self.feedback.append(feedback)
        if feedback.parent is not None:
            feedback.parent._get_child_feedback(feedback, True)
        return feedback

    def add_ignored_feedback(self, feedback):
        """
        Attaches the given feedback object to this report, but only in the
        ignored list. That means it should not be considered by the Resolver,
        since its condition did not apply to the code. Some Resolvers like
        to know about feedback that was not reached.

        Args:
            feedback (:py:class:`~pedal.core.feedback.Feedback`): The feedback
                object to attach.

        Returns:
            :py:class:`~pedal.core.feedback.Feedback`: The attached feedback.
        """
        self.ignored_feedback.append(feedback)
        if feedback.parent is not None:
            feedback.parent._get_child_feedback(feedback, False)
        return feedback

    def suppress(self, category=None, label=True):
        """
        Suggest that an entire category or label within a category ignored by
        the resolver.
        TODO: Currently, only global suppression is supported.

        Args:
            category (str): The category of feedback to suppress.
            label (bool or str): A specific label to match against and suppress.
        """
        if category is None:
            self.suppressed_labels.append(label)
        else:
            category = category.lower()
            if isinstance(label, str):
                label = label.lower()
            if category in FeedbackCategory.ALIASES:
                category = FeedbackCategory.ALIASES[category]
            if category not in self.suppressions:
                self.suppressions[category] = []
            self.suppressions[category].append(label)

    def add_hook(self, event, function):
        """
        Register the `function` to be executed when the given `event` is
        triggered.
        
        Args:
            event (str): An event name. Multiple functions can be triggered for
                the same `event`. The format is as follows: `"namespace.function.extra"`
                The `".extra"` component is optional to add further nuance, but
                the general idea is that you are referring to functions that,
                when called, should trigger other functions to be called first.
                The namespace is typically a tool or module.
            function (callable): A callable function. This function should
                accept a keyword parameter named `report`; this report will be passed
                as as that argument.
        """
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(function)

    @classmethod
    def add_class_hook(cls, event, function):
        """ Similar to ``add_hook``, except attaches them to the class, so
        they will be executed for ALL report subclasses. """
        if event not in cls.class_hooks:
            cls.class_hooks[event] = []
        cls.class_hooks[event].append(function)

    def execute_hooks(self, tool, event_name):
        """
        Trigger the functions for all of the associated hooks.
        Hooks will be called with this report as a keyword `report` argument.

        Args:
            tool (str): The name of the tool, to namespace events by.
            event_name (str): The event name (separate words with periods).
        """
        event = tool + '.' + event_name
        if event in self.class_hooks:
            for function in self.class_hooks[event]:
                function(report=self)
        if event in self.hooks:
            for function in self.hooks[event]:
                function(report=self)

    def __getitem__(self, tool_name):
        """
        Support retrieving a tool's data from the report using square bracket
        syntax. So, for example, you can do `MAIN_REPORT['tifa']` and get its
        data dictionary. If the tool has been registered, but not initialized
        for this report, then the tool will be
        :py:method:`pedal.core.tool.reset` first. Otherwise, throws an error
        that the tool does not exist.

        Args:
            tool_name (str): The formal name of the tool, most likely specified
                in its `constants.py` file.

        Returns:
            dict: The data associated with that tool.
        """
        if tool_name not in self._tool_data:
            if tool_name not in self.TOOLS:
                raise PedalToolNotRegistered(tool_name, list(self.TOOLS.keys()))
            self.TOOLS[tool_name].reset(report=self)
        return self._tool_data[tool_name]

    def __setitem__(self, tool_name, value):
        """
        Update the tool's current data. Should largely not be used by anyone.
        In fact, this could seriously damage the relationships between tools.

        Args:
            tool_name (str): The name of the tool.
            value (dict): The new data to set as this tool's namespace.
        """
        self._tool_data[tool_name] = value

    def __contains__(self, tool_name):
        """
        Determine if the given `tool_name` is available through this report.
        Args:
            tool_name (str): The name of a tool.

        Returns:
            bool: Whether the tool is available.
        """
        return tool_name in self._tool_data

    def set_formatter(self, formatter):
        """
        Update the formatter with the new option.

        Args:
            formatter (:py:class:`pedal.core.formatting.Formatter`): The new
                formatter to use.
        """
        self.format = formatter

    @classmethod
    def register_tool(cls, tool_name: str, reset_function):
        """
        Identifies that the given Tool should be made available.
        Args:
            tool_name: A unique string identifying this tool.
            reset_function: The function to call to reset the Tool.

        Returns:

        """
        if tool_name in cls.TOOLS:
            raise PedalToolAlreadyRegistered(tool_name)
        cls.TOOLS[tool_name] = ToolRegistration(tool_name, reset_function)

    def get_current_group(self):
        if self.groups:
            return self.groups[-1]
        else:
            return None

    def start_group(self, group):
        self.groups.append(group)

    def stop_group(self, group):
        if self.groups:
            self.groups.remove(group)


#: The global Report object. Meant to be used as a default singleton
#: for any tool, so that instructors do not have to create their own Report.
#: Of course, all APIs are expected to work with a given Report, and only
#: default to this Report when no others are given.
#: Ideally, the average instructor will never know this exists.
MAIN_REPORT = Report()

# TODO: Give a mechanism for "freezing" a report that you can keep around.
