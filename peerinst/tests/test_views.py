# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import random

from django.core.urlresolvers import reverse
from django.test import TestCase
from django_lti_tool_provider.models import LtiUserData
from django_lti_tool_provider.views import LTIView

import ddt
import mock

from ..util import SessionStageData
from . import factories


class Grade(object):
    CORRECT = 1.0
    INCORRECT = 0.0
    PARTIAL = 0.5


class QuestionViewTestCase(TestCase):

    ORG = 'LTIX'
    COURSE_ID = 'course-v1:{org}+LTI-101+now'.format(org=ORG)
    USAGE_ID = 'block-v1:LTIX+LTI-101+now+type@lti+block@d41d8cd98f00b204e9800998ecf8427e'
    LTI_PARAMS = {
        'context_id': COURSE_ID,
        'lis_outcome_service_url': ('https://courses.edx.org/courses/{course_id}/xblock/{usage_id}'
            '/handler_noauth/grade_handler').format(course_id=COURSE_ID, usage_id=USAGE_ID),
        'lis_result_sourcedid': 'lis_result_sourcedid',
        'lti_version': 'LTI-1p0',
        'resource_link_id': 'resource_link_id',
        'user_id': '1234567890',
    }

    def setUp(self):
        super(QuestionViewTestCase, self).setUp()
        self.user = factories.UserFactory()
        self.assignment = factories.AssignmentFactory()
        self.set_question(factories.QuestionFactory(
            choices=5, choices__correct=[2, 4], choices__rationales=4,
        ))
        self.addCleanup(mock.patch.stopall)
        signal_patcher = mock.patch('django_lti_tool_provider.signals.Signals.Grade.updated.send')
        self.mock_send_grade_signal = signal_patcher.start()
        grade_patcher = mock.patch('peerinst.models.Answer.get_grade')
        self.mock_get_grade = grade_patcher.start()
        self.mock_get_grade.return_value = Grade.CORRECT

    def set_question(self, question):
        self.question = question
        self.assignment.questions.add(question)
        self.answer_choices = question.get_choices()
        self.question_url = reverse(
            'question', kwargs=dict(assignment_id=self.assignment.pk, question_id=question.pk)
        )
        self.custom_key = unicode(self.assignment.pk) + ':' + unicode(question.pk)
        self.log_in_with_lti()

    def log_in_with_scoring_disabled(self):
        """
        Log a user in pretending that scoring is disabled in the LMS.

        This is done by calling `log_in_with_lti` with a modified version of `LTI_PARAMS`
        that does not include `lis_outcome_service_url`.

        `lis_outcome_service_url` is the URL of the handler to use for sending grades to the LMS.
        It is only included in the LTI request if grading is enabled on the LMS side
        (otherwise there is no need to send back a grade).
        """
        lti_params = self.LTI_PARAMS.copy()
        del lti_params['lis_outcome_service_url']
        self.log_in_with_lti(lti_params=lti_params)

    def log_in_with_lti(self, user=None, password=None, lti_params=None):
        """Log a user in with fake LTI data."""
        if user is None:
            user = self.user
        if lti_params is None:
            lti_params = self.LTI_PARAMS.copy()
        lti_params['lis_person_sourcedid'] = user.username
        lti_params['lis_person_contact_email_primary'] = user.email
        lti_params['custom_assignment_id'] = unicode(self.assignment.pk)
        lti_params['custom_question_id'] = unicode(self.question.pk)
        LtiUserData.store_lti_parameters(user, LTIView.authentication_manager, lti_params)
        self.client.login(username=user.username, password=password or 'test')

    def question_get(self):
        response = self.client.get(self.question_url)
        self.assertEqual(response.status_code, 200)
        return response

    def question_post(self, **form_data):
        response = self.client.post(self.question_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        return response


class QuestionViewTest(QuestionViewTestCase):

    def assert_grade_signal(self, grade=Grade.INCORRECT):
        send = mock.call('peerinst.views', user=self.user, custom_key=self.custom_key, grade=grade)
        self.assertEqual(self.mock_send_grade_signal.call_args_list, [send] * 2)

    def run_standard_review_mode(self):
        """Test answering questions in default mode."""

        # Show the question and the form for the first answer and rationale.
        response = self.question_get()
        self.assertTemplateUsed(response, 'peerinst/question_start.html')
        self.assertEqual(response.context['assignment'], self.assignment)
        self.assertEqual(response.context['question'], self.question)
        self.assertEqual(response.context['answer_choices'], self.answer_choices)

        # Provide a first answer and a rationale.
        first_answer_choice = 2
        first_choice_label = self.question.get_choice_label(2)
        rationale = 'my rationale text'
        response = self.question_post(first_answer_choice=first_answer_choice, rationale=rationale)
        self.assertTemplateUsed(response, 'peerinst/question_review.html')
        self.assertEqual(response.context['assignment'], self.assignment)
        self.assertEqual(response.context['question'], self.question)
        self.assertEqual(response.context['answer_choices'], self.answer_choices)
        self.assertEqual(response.context['first_choice_label'], first_choice_label)
        self.assertEqual(response.context['rationale'], rationale)
        self.assertEqual(response.context['sequential_review'], False)
        stage_data = SessionStageData(self.client.session, self.custom_key)
        rationale_choices = stage_data.get('rationale_choices')
        second_answer_choices = [
            choice for choice, unused_label, unused_rationales in rationale_choices
        ]
        self.assertIn(first_answer_choice, second_answer_choices)

        # Select a different answer during review.
        second_answer_choice = next(
            choice for choice in second_answer_choices if choice != first_answer_choice
        )
        second_choice_label = self.question.get_choice_label(second_answer_choice)
        chosen_rationale = int(rationale_choices[1][2][0][0])
        response = self.question_post(
            second_answer_choice=second_answer_choice,
            rationale_choice_1=chosen_rationale,
        )
        self.assertTemplateUsed(response, 'peerinst/question_summary.html')
        self.assertEqual(response.context['assignment'], self.assignment)
        self.assertEqual(response.context['question'], self.question)
        self.assertEqual(response.context['answer_choices'], self.answer_choices)
        self.assertEqual(response.context['first_choice_label'], first_choice_label)
        self.assertEqual(response.context['second_choice_label'], second_choice_label)
        self.assertEqual(response.context['rationale'], rationale)
        self.assertEqual(response.context['chosen_rationale'].id, chosen_rationale)

    def test_standard_review_mode(self):
        """Test answering questions in default mode, with scoring enabled."""
        self.mock_get_grade.return_value = Grade.INCORRECT
        self.run_standard_review_mode()
        self.assert_grade_signal()
        self.assertTrue(self.mock_get_grade.called)

    def test_standard_review_mode_scoring_disabled(self):
        """Test answering questions in default mode, with scoring disabled."""
        self.log_in_with_scoring_disabled()
        self.run_standard_review_mode()
        self.assertFalse(self.mock_send_grade_signal.called)
        self.assertTrue(self.mock_get_grade.called)  # "emit_check_events" still uses "get_grade" to obtain grade data

    def test_sequential_review_mode(self):
        """Test answering questions in sequential review mode."""

        self.mock_get_grade.return_value = Grade.INCORRECT

        self.set_question(factories.QuestionFactory(
            sequential_review=True,
            choices=5, choices__correct=[2, 4], choices__rationales=4,
        ))

        # Show the question and the form for the first answer and rationale.
        response = self.question_get()
        self.assertTemplateUsed(response, 'peerinst/question_start.html')
        self.assertEqual(response.context['assignment'], self.assignment)
        self.assertEqual(response.context['question'], self.question)
        self.assertEqual(response.context['answer_choices'], self.answer_choices)

        # Provide a first answer and a rationale.
        first_answer_choice = 2
        first_choice_label = self.question.get_choice_label(2)
        rationale = 'my rationale text'
        response = self.question_post(first_answer_choice=first_answer_choice, rationale=rationale)

        # Loop over all rationales and vote on them.
        votes = []
        while 'peerinst/question_sequential_review.html' in (
                template.name for template in response.templates
            ):
            self.assertTrue(response.context['current_rationale'])
            vote = random.choice(['upvote', 'downvote'])
            votes.append(vote)
            response = self.question_post(**{vote: 1})

        # We've reached the final review.
        self.assertTemplateUsed(response, 'peerinst/question_review.html')
        self.assertEqual(response.context['assignment'], self.assignment)
        self.assertEqual(response.context['question'], self.question)
        self.assertEqual(response.context['answer_choices'], self.answer_choices)
        self.assertEqual(response.context['first_choice_label'], first_choice_label)
        self.assertEqual(response.context['rationale'], rationale)
        self.assertEqual(response.context['sequential_review'], True)
        stage_data = SessionStageData(self.client.session, self.custom_key)
        rationale_choices = stage_data.get('rationale_choices')
        second_answer_choices = [
            choice for choice, unused_label, unused_rationales in rationale_choices
        ]
        self.assertIn(first_answer_choice, second_answer_choices)

        # Select a different answer during review.
        second_answer_choice = next(
            choice for choice in second_answer_choices if choice != first_answer_choice
        )
        second_choice_label = self.question.get_choice_label(second_answer_choice)
        chosen_rationale = int(rationale_choices[1][2][0][0])
        response = self.question_post(
            second_answer_choice=second_answer_choice,
            rationale_choice_1=chosen_rationale,
        )
        self.assertTemplateUsed(response, 'peerinst/question_summary.html')
        self.assertEqual(response.context['assignment'], self.assignment)
        self.assertEqual(response.context['question'], self.question)
        self.assertEqual(response.context['answer_choices'], self.answer_choices)
        self.assertEqual(response.context['first_choice_label'], first_choice_label)
        self.assertEqual(response.context['second_choice_label'], second_choice_label)
        self.assertEqual(response.context['rationale'], rationale)
        self.assertEqual(response.context['chosen_rationale'].id, chosen_rationale)

        self.assert_grade_signal()
        self.assertTrue(self.mock_get_grade.called)


@ddt.ddt
class EventLogTest(QuestionViewTestCase):

    def verify_event(self, logger, scoring_disabled=False):
        self.assertTrue(logger.info.called)
        event = json.loads(logger.info.call_args[0][0])
        self.assertEqual(event['context']['course_id'], self.COURSE_ID)
        self.assertEqual(event['context']['module']['usage_key'], None if scoring_disabled else self.USAGE_ID)
        self.assertEqual(event['context']['org_id'], self.ORG)
        self.assertEqual(event['event']['assignment_id'], self.assignment.pk)
        self.assertEqual(event['event']['question_id'], self.question.pk)
        self.assertEqual(event['username'], self.user.username)
        if scoring_disabled:
            self.assertIsNone(event['event'].get('grade'))
            self.assertIsNone(event['event'].get('max_grade'))
        return event

    def _test_events(self, logger, scoring_disabled=False, grade=Grade.CORRECT):
        # Show the question and verify the logged event.
        response = self.question_get()
        event = self.verify_event(logger, scoring_disabled=scoring_disabled)
        self.assertEqual(event['event_type'], 'problem_show')
        logger.reset_mock()

        # Provide a first answer and a rationale, and verify the logged event.
        response = self.question_post(first_answer_choice=2, rationale='my rationale text')
        event = self.verify_event(logger, scoring_disabled=scoring_disabled)
        self.assertEqual(event['event_type'], 'problem_check')
        self.assertEqual(event['event']['first_answer_choice'], 2)
        self.assertEqual(event['event']['success'], 'correct')
        self.assertEqual(event['event']['rationale'], 'my rationale text')
        logger.reset_mock()

        # Select our own rationale and verify the logged event
        response = self.question_post(second_answer_choice=2, rationale_choice_0=None)
        event = self.verify_event(logger, scoring_disabled=scoring_disabled)
        self.assertEqual(logger.info.call_count, 2)
        self.assertEqual(event['event_type'], 'save_problem_success')
        self.assertEqual(event['event']['success'], 'correct' if grade == Grade.CORRECT else 'incorrect')

        if not scoring_disabled:
            self.assertEqual(event['event']['grade'], grade)
            self.assertEqual(event['event']['max_grade'], Grade.CORRECT)

    @ddt.data(Grade.CORRECT, Grade.INCORRECT, Grade.PARTIAL)
    @mock.patch('peerinst.views.LOGGER')
    def test_events_scoring_enabled(self, grade, logger):
        self.mock_get_grade.return_value = grade
        self._test_events(logger, grade=grade)

    @mock.patch('peerinst.views.LOGGER')
    def test_events_scoring_disabled(self, logger):
        self.log_in_with_scoring_disabled()
        self._test_events(logger, scoring_disabled=True)
