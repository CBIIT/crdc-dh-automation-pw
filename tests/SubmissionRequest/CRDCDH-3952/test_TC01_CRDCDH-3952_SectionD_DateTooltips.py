"""CRDCDH-3952 — Section D targeted delivery and expected publication date tooltips.

Xray CRDCDH-3952 (FE CRDCDH-3978). hub is already signed in as Submitter.
May fail on QA until updated tooltip copy is deployed; expected vs actual are logged.
"""

from __future__ import annotations

import logging

import pytest

from crdc_pw.hub import Hub
from crdc_pw.pages.submission_request_form import (
    SR_SECTION_D_EXPECTED_PUB_TOOLTIP,
    SR_SECTION_D_TARGETED_DELIVERY_TOOLTIP,
    SubmissionRequestFormPage,
)
from crdc_pw.pages.submission_requests_list import SubmissionRequestsListPage
from crdc_pw.utils.ui_helpers import verify_tooltip_on_click

log = logging.getLogger("crdc_pw.tc_crdcdh_3952")

pytestmark = pytest.mark.CRDC_SubmissionRequests

_TARGETED_TOOLTIP = (
    "CRDC/AILocators/SubmissionRequests/Form/SectionD/TargetedDeliveryDate-TooltipTrigger"
)
_EXPECTED_PUB_TOOLTIP = (
    "CRDC/AILocators/SubmissionRequests/Form/SectionD/ExpectedPubDate-TooltipTrigger"
)


@pytest.mark.parametrize("hub", ["Submitter"], indirect=True)
def test_TC01_CRDCDH_3952_SectionD_DateTooltips(hub: Hub) -> None:
    hub.page.set_viewport_size({"width": 1920, "height": 1080})

    sr_list = SubmissionRequestsListPage(hub.page, hub.locators)
    form = SubmissionRequestFormPage(hub.page, hub.locators)

    # Step 1: Start a new Submission Request — verify status bar shows NEW.
    sr_list.open()
    sr_list.start_new_submission_request()
    form.assert_status("NEW")

    # Step 2: Open Section D (Release & Delivery dates) via progress bar.
    form.click_progress_bar_section_d()

    # Step 3: Targeted Data Submission Delivery Date info icon — full tooltip matches CRDCDH-3952 copy.
    verify_tooltip_on_click(
        hub.page,
        hub.page.locator(hub.locators.get(_TARGETED_TOOLTIP)),
        SR_SECTION_D_TARGETED_DELIVERY_TOOLTIP,
    )
    # Step 4: Expected Publication Date info icon — full tooltip matches CRDCDH-3952 copy.
    verify_tooltip_on_click(
        hub.page,
        hub.page.locator(hub.locators.get(_EXPECTED_PUB_TOOLTIP)),
        SR_SECTION_D_EXPECTED_PUB_TOOLTIP,
    )

    log.info("PASS CRDCDH-3952 TC01 as %s", hub.role)
