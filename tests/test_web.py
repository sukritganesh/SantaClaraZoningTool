"""Focused tests for the Block 7.4a Flask shell and route boundary."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from santa_clara_zoning import PipelineIntegrityError, RulesetLoadError
from santa_clara_zoning.lookup import DEFAULT_ADDRESS_SNAPSHOT, DEFAULT_R1_SNAPSHOT
from santa_clara_zoning.web import create_app


SNAPSHOTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "parcels_r1.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "current_zoning_r1.geojson").is_file()
)


def _view(kind: str = "success") -> dict:
    return {
        "kind": kind,
        "overview": {
            "headline": "Fixture headline",
            "summary": "Fixture summary",
        },
    }


class WebShellTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = Mock()
        self.app = create_app(self.pipeline)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_landing_page_does_not_run_the_pipeline(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn('name="address"', response.get_data(as_text=True))
        self.assertNotIn("data-result-kind", response.get_data(as_text=True))
        self.pipeline.analyze_address.assert_not_called()

    def test_address_runs_pipeline_and_presenter_once(self) -> None:
        pipeline_result = {"fixture": "pipeline result"}
        self.pipeline.analyze_address.return_value = pipeline_result

        with patch(
            "santa_clara_zoning.web.present_pipeline_result",
            return_value=_view(),
        ) as presenter:
            response = self.client.get("/", query_string={"address": "636 Barto St"})

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="success"', response.get_data(as_text=True))
        self.assertIn('value="636 Barto St"', response.get_data(as_text=True))
        self.pipeline.analyze_address.assert_called_once_with("636 Barto St")
        presenter.assert_called_once_with(pipeline_result)

    def test_same_injected_pipeline_is_reused_across_requests(self) -> None:
        self.pipeline.analyze_address.return_value = {"fixture": True}

        with patch(
            "santa_clara_zoning.web.present_pipeline_result",
            return_value=_view(),
        ):
            self.client.get("/", query_string={"address": "First address"})
            self.client.get("/", query_string={"address": "Second address"})

        self.assertIs(
            self.app.extensions["r1_standards_pipeline"],
            self.pipeline,
        )
        self.assertEqual(self.pipeline.analyze_address.call_count, 2)

    def test_known_integrity_error_becomes_safe_system_view(self) -> None:
        self.pipeline.analyze_address.side_effect = PipelineIntegrityError(
            "fixture_integrity_error",
            "private diagnostic detail",
        )

        response = self.client.get("/", query_string={"address": "636 Barto St"})
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="system_error"', body)
        self.assertIn("System or data validation error", body)
        self.assertNotIn("private diagnostic detail", body)

    def test_unexpected_error_is_not_relabelled(self) -> None:
        self.pipeline.analyze_address.side_effect = RuntimeError("programming defect")

        with self.assertRaisesRegex(RuntimeError, "programming defect"):
            self.client.get("/", query_string={"address": "636 Barto St"})

    def test_entered_address_is_html_escaped(self) -> None:
        self.pipeline.analyze_address.return_value = {"fixture": True}
        entered = '<script>alert("x")</script>'

        with patch(
            "santa_clara_zoning.web.present_pipeline_result",
            return_value=_view("lookup_failure"),
        ):
            response = self.client.get("/", query_string={"address": entered})

        body = response.get_data(as_text=True)
        self.assertNotIn(entered, body)
        self.assertIn("&lt;script&gt;", body)

    def test_post_is_not_an_application_route(self) -> None:
        response = self.client.post("/", data={"address": "636 Barto St"})

        self.assertEqual(response.status_code, 405)
        self.pipeline.analyze_address.assert_not_called()


class WebStartupFailureTest(unittest.TestCase):
    def test_ruleset_startup_failure_is_presented_after_search(self) -> None:
        failure = RulesetLoadError("fixture gate", ["private diagnostic detail"])
        with patch(
            "santa_clara_zoning.web.R1StandardsPipeline.from_defaults",
            side_effect=failure,
        ):
            app = create_app()
        app.config.update(TESTING=True)

        response = app.test_client().get(
            "/",
            query_string={"address": "636 Barto St"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="system_error"', body)
        self.assertNotIn("private diagnostic detail", body)


@unittest.skipUnless(SNAPSHOTS_AVAILABLE, "canonical raw GIS snapshots are not present")
class WebShellIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.app.config.update(TESTING=True)

    def test_default_app_runs_real_barto_pipeline_and_presenter(self) -> None:
        response = self.app.test_client().get(
            "/",
            query_string={"address": "636 Barto Street"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="success"', body)
        self.assertIn("R1-6L base-zone standards", body)


if __name__ == "__main__":
    unittest.main()
