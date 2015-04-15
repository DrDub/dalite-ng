from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

class FirstAnswerForm(forms.Form):
    """Form to select one of the answer choices and enter a rationale."""

    first_answer_choice = forms.ChoiceField(widget=forms.RadioSelect)
    rationale = forms.CharField(widget=forms.Textarea)

    def __init__(self, answer_choices, *args, **kwargs):
        choice_texts = [mark_safe(". ".join(pair)) for pair in answer_choices]
        self.base_fields['first_answer_choice'].choices = enumerate(choice_texts, 1)
        forms.Form.__init__(self, *args, **kwargs)

    def clean_first_answer_choice(self):
        choice = self.cleaned_data['first_answer_choice']
        try:
            choice = int(choice)
        except ValueError:
            # This can only happen for manually crafted requests.
            raise forms.ValidationError('Answer choice must be an integer.')
        return choice

class ReviewAnswerForm(forms.Form):
    """Form on the answer review page."""

    second_answer_choice = forms.ChoiceField(widget=forms.RadioSelect)
    rationale_choice_0 = forms.ChoiceField(required=False, widget=forms.RadioSelect)
    rationale_choice_1 = forms.ChoiceField(required=False, widget=forms.RadioSelect)

    def __init__(self, answer_choices, display_rationales, *args, **kwargs):
        self.base_fields['second_answer_choice'].choices = answer_choices
        for i, rationales in enumerate(display_rationales):
            self.base_fields['rationale_choice_{}'.format(i)].choices = [
                (r.id, r.rationale) for r in rationales
            ]
        forms.Form.__init__(self, *args, **kwargs)

    def clean_second_answer_choice(self):
        choice = self.cleaned_data['second_answer_choice']
        try:
            choice = int(choice)
        except ValueError:
            # This can only happen for manually crafted requests.
            raise forms.ValidationError('Answer choice must be an integer.')
        return choice

    def clean(self):
        cleaned_data = forms.Form.clean(self)
        if sum(bool(cleaned_data.get('rationale_choice_{}'.format(i), 0)) for i in range(2)) != 1:
            # This should be prevented by the UI on the client side, so this check is mostly to
            # protect against bugs and people transferring made-up data.
            raise forms.ValidationError(_('Please select exactly one rationale.'))
        chosen_rationale_id = (
            cleaned_data.get('rationale_choice_0', None) or cleaned_data.get('rationale_choice_1')
        )
        cleaned_data.update(chosen_rationale_id=chosen_rationale_id)
        return cleaned_data