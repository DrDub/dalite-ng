# -*- coding: utf-8 -*-
from __future__ import division, unicode_literals

from django.test import TestCase
from .. import admin_views
from .. import models


class AggregatesTestCase(TestCase):
    fixtures = ['peerinst_test_data']

    def test_get_question_aggregates(self):
        assignment = models.Assignment.objects.get(identifier='Assignment1')

        question = models.Question.objects.get(id=29)
        sums, students = admin_views.get_question_aggregates(assignment, question)
        expected_sums = {
            'correct_first_answers': 6,
            'correct_second_answers': 3,
            'switches': 9,
            ('switches', 1): 2,
            ('switches', 2): 1,
            ('switches', 3): 3,
            ('switches', 4): 3,
            'total_answers': 14,
        }
        self.assertDictEqual(dict(sums), expected_sums)
        expected_students = {
            'bmnwf', 'eeawg', 'esbxa', 'kmhti', 'nrqek', 'qsrzd', 'rhtof', 'upjwt', 'yosbj'
        }
        self.assertSetEqual(students, expected_students)

        question = models.Question.objects.get(id=30)
        sums, students = admin_views.get_question_aggregates(assignment, question)
        expected_sums = {
            'correct_first_answers': 3,
            'correct_second_answers': 3,
            'switches': 6,
            ('switches', 1): 3,
            ('switches', 2): 3,
            'total_answers': 6,
        }
        self.assertDictEqual(dict(sums), expected_sums)
        expected_students = {'askvw', 'ciuaq', 'etgfe', 'glepb', 'kmhti', 'nrqek'}
        self.assertSetEqual(students, expected_students)

    def test_get_assignment_aggregates(self):
        assignment = models.Assignment.objects.get(identifier='Assignment1')

        sums, unused_question_data = admin_views.get_assignment_aggregates(assignment)
        expected_sums = {
            'correct_first_answers': 9,
            'correct_second_answers': 6,
            'switches': 15,
            ('switches', 1): 5,
            ('switches', 2): 4,
            ('switches', 3): 3,
            ('switches', 4): 3,
            'total_answers': 20,
            'total_students': 13,
        }
        self.assertDictEqual(dict(sums), expected_sums)
