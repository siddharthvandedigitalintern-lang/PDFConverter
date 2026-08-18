import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
import importlib.machinery
import importlib.util
loader = importlib.machinery.SourceFileLoader("notes_ninja", "app.py")
spec = importlib.util.spec_from_loader("notes_ninja", loader)
notes_ninja = importlib.util.module_from_spec(spec)
loader.exec_module(notes_ninja)


class FormatPdfTest(unittest.TestCase):
    def setUp(self):
        self.client = notes_ninja.app.test_client()

    def test_rejects_non_pdf(self):
        response = self.client.post(
            "/format",
            data={"pdf": (io.BytesIO(b"hello"), "notes.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

    @patch.object(notes_ninja, "validate_rendered_content")
    @patch.object(notes_ninja, "render_pdf")
    @patch.object(notes_ninja, "extract_segments_layout")
    def test_returns_generated_pdf(self, extract_segments_layout, render_pdf, _validate):
        import time
        generated = []
        rendered_html = []
        extract_segments_layout.return_value = [
            {"id": 1, "page": 1, "type": "text", "text": "Title", "font_size": 18, "is_bold": True},
            {"id": 2, "page": 1, "type": "text", "text": "Body", "font_size": 12, "is_bold": False},
        ]
        def fake_render(html, path):
            generated.append(path)
            rendered_html.append(html)
            doc = fitz.open()
            doc.new_page()
            doc.save(path)
            doc.close()

        render_pdf.side_effect = fake_render
        response = self.client.post(
            "/format",
            data={"pdf": (io.BytesIO(b"%PDF-1.4"), "notes.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 202)
        data = response.json
        job_id = data.get("job_id")
        self.assertIsNotNone(job_id)
        response.close()

        # Poll status until completed
        for _ in range(50):
            status_resp = self.client.get(f"/status/{job_id}")
            self.assertEqual(status_resp.status_code, 200)
            status_data = status_resp.json
            if status_data.get("status") == "completed":
                break
            time.sleep(0.1)
        else:
            self.fail("Job did not complete in time")

        # Download PDF
        download_resp = self.client.get(f"/download/{job_id}")
        self.assertEqual(download_resp.status_code, 200)
        self.assertEqual(download_resp.mimetype, "application/pdf")
        self.assertIn("filename=notes.pdf", download_resp.headers["Content-Disposition"])
        self.assertTrue(download_resp.data.startswith(b"%PDF"))
        self.assertIn('<h1 class="cover-title">Title</h1>', rendered_html[0])
        download_resp.close()

    def test_branded_pdf_preserves_pages_and_source_text(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.pdf"
            output_path = Path(directory) / "output.pdf"
            source = fitz.open()
            for text in ("First page exact content", "Second page exact content"):
                page = source.new_page(width=300, height=400)
                page.insert_text((30, 50), text, fontsize=16)
            source.save(source_path)
            source.close()

            notes_ninja.render_branded_pdf(source_path, output_path)
            with fitz.open(source_path) as original, fitz.open(output_path) as branded:
                self.assertEqual(len(branded), len(original) + 1)
                for index in range(len(original)):
                    self.assertIn(original[index].get_text().strip(), branded[index + 1].get_text())
                    self.assertEqual(branded[index + 1].rect, original[index].rect)

    def test_mcq_card_removes_layout_whitespace_without_rewriting_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "mcq.pdf"
            output_path = Path(directory) / "formatted.pdf"
            source = fitz.open()
            page = source.new_page(width=595.28, height=841.89)
            page.insert_textbox(
                fitz.Rect(60, 60, 535, 300),
                "Q1. A    One-Tailed Test    is used when?\n"
                "a) First option\nb) Second option\nc) Third option\nd) Fourth option\n"
                "Answer: (b) Second option",
                fontsize=10.5,
            )
            source.save(source_path)
            source.close()

            notes_ninja.render_branded_pdf(source_path, output_path, "MCQ Notes")
            with fitz.open(output_path) as formatted:
                text = formatted[1].get_text()
                self.assertIn("A One-Tailed Test is used when?", text)
                self.assertIn("Answer: (b) Second option", text)
                self.assertNotIn("Answer: Answer:", text)

    def test_mcq_split_across_pages_is_detected_as_one_card(self):
        document = fitz.open()
        first = document.new_page(width=300, height=400)
        first.insert_textbox(
            fitz.Rect(30, 40, 270, 350),
            "Q3. A cross-page question?\na) First\nb) Second",
            fontsize=11,
        )
        second = document.new_page(width=300, height=400)
        second.insert_textbox(
            fitz.Rect(30, 40, 270, 350),
            "c) Third\nd) Fourth\nAnswer: (b) Second\nQ4. Next question?",
            fontsize=11,
        )
        layout = notes_ninja._cross_page_mcqs(document)
        self.assertEqual(layout[1]["cards"][0]["number"], "3")
        self.assertEqual(layout[1]["cards"][0]["answer"], "B")
        document.close()

    def test_build_document_cannot_rewrite_or_omit_segments(self):
        segments = [
            {"id": 1, "page": 1, "text": "Exact Title"},
            {"id": 2, "page": 1, "text": "Unit Eight"},
            {"id": 3, "page": 1, "text": "Original paragraph words."},
            {"id": 4, "page": 2, "text": "Unclassified text is preserved."},
        ]
        classification = {
            "title_segment_id": 1,
            "unit_headings": [{"segment_id": 2, "unit_number": 8}],
            "heading_segment_ids": [],
            "mcq_segment_ids": [],
            "qa_segment_ids": [],
        }

        document = notes_ninja.build_document(segments, classification)
        self.assertEqual(document["title"], segments[0]["text"])
        self.assertEqual(document["front_matter"], [])
        self.assertEqual(document["units"][0]["heading"], segments[1]["text"])
        self.assertEqual(
            [item["text"] for item in document["units"][0]["content"]],
            [segments[2]["text"], segments[3]["text"]],
        )

    def test_answer_blocks_receive_green_theme_marker(self):
        document = notes_ninja.build_document(
            [
                {"id": 1, "page": 1, "text": "Title"},
                {"id": 2, "page": 1, "text": "Answer: (c) Two-Tailed Test"},
            ],
            {
                "title_segment_id": 1,
                "unit_headings": [],
                "heading_segment_ids": [],
                "mcq_segment_ids": [],
                "qa_segment_ids": [],
            },
        )
        self.assertTrue(document["units"][0]["content"][0]["is_answer"])

        prose = notes_ninja.build_document(
            [
                {"id": 1, "page": 1, "text": "Title"},
                {"id": 2, "page": 1, "text": "Answers vary according to the data."},
            ],
            {
                "title_segment_id": 1,
                "unit_headings": [],
                "heading_segment_ids": [],
                "mcq_segment_ids": [],
                "qa_segment_ids": [],
            },
        )
        self.assertFalse(prose["units"][0]["content"][0]["is_answer"])

    def test_mcq_question_options_and_answer_become_one_card(self):
        segments = [
            {"id": 1, "page": 1, "text": "Title"},
            {"id": 2, "page": 1, "text": "Q1. Choose the correct option:"},
            {"id": 3, "page": 1, "text": "a) First option"},
            {"id": 4, "page": 1, "text": "Answer: (a) First option"},
        ]
        document = notes_ninja.build_document(
            segments,
            {
                "title_segment_id": 1,
                "unit_headings": [],
                "heading_segment_ids": [],
                "mcq_segment_ids": [2, 3, 4],
                "qa_segment_ids": [],
            },
        )
        items = document["units"][0]["content"]
        self.assertEqual([item["type"] for item in items], ["mcq"])
        self.assertEqual(items[0]["question"], segments[1]["text"])
        self.assertEqual(items[0]["options"], [{"label": "a", "text": "First option"}])
        self.assertEqual(items[0]["answer"], "(a) First option")

    def test_source_font_hierarchy_promotes_large_bold_text(self):
        document = notes_ninja.build_document(
            [
                {"id": 1, "page": 1, "type": "text", "text": "Title", "font_size": 18, "is_bold": True},
                {"id": 2, "page": 1, "type": "text", "text": "Normal paragraph with enough body text to establish the source body size.", "font_size": 12, "is_bold": False},
                {"id": 3, "page": 1, "type": "text", "text": "Important Heading", "font_size": 14, "is_bold": True},
            ],
            {
                "title_segment_id": 1,
                "unit_headings": [],
                "heading_segment_ids": [],
                "mcq_segment_ids": [],
                "qa_segment_ids": [],
            },
        )
        self.assertEqual([item["type"] for item in document["units"][0]["content"]], ["paragraph", "heading"])

    def test_lists_and_diagrams_keep_their_structure(self):
        document = notes_ninja.build_document(
            [
                {"id": 1, "page": 1, "type": "text", "text": "Title"},
                {
                    "id": 2,
                    "page": 1,
                    "type": "text",
                    "text": "1. First\n2. Second\n3. Third",
                    "preserve_lines": True,
                },
                {"id": 3, "page": 1, "type": "image", "src": "file:///diagram.jpg"},
            ],
            {
                "title_segment_id": 1,
                "unit_headings": [],
                "heading_segment_ids": [],
                "mcq_segment_ids": [],
                "qa_segment_ids": [],
            },
        )
        items = document["units"][0]["content"]
        self.assertTrue(items[0]["preserve_lines"])
        self.assertEqual(items[1], {"type": "image", "src": "file:///diagram.jpg"})

    def test_local_fallback_detects_roman_unit_and_uses_subject_as_title(self):
        classification = notes_ninja.local_classification([
            {"id": 1, "page": 1, "type": "text", "text": "Unit - II"},
            {"id": 2, "page": 1, "type": "text", "text": "Software Process and SDLC Models"},
        ])
        self.assertEqual(classification["title_segment_id"], 2)
        self.assertEqual(classification["unit_headings"], [{"segment_id": 1, "unit_number": 2}])

    def test_local_fallback_classifies_all_study_sections(self):
        segments = [
            {"id": 1, "page": 1, "type": "text", "text": "Statistics for Managers", "font_size": 18, "is_bold": True},
            {"id": 2, "page": 2, "type": "text", "text": "Unit 8: Hypothesis", "font_size": 20, "is_bold": True},
            {"id": 3, "page": 2, "type": "text", "text": "DETAILED NOTES", "font_size": 13, "is_bold": True},
            {"id": 4, "page": 3, "type": "text", "text": "Multiple Choice Questions (MCQs)", "font_size": 13, "is_bold": True},
            {"id": 5, "page": 3, "type": "text", "text": "Q1. Choose one", "font_size": 10.5, "is_bold": True},
            {"id": 6, "page": 4, "type": "text", "text": "Short Answer Questions", "font_size": 13, "is_bold": True},
            {"id": 7, "page": 4, "type": "text", "text": "1. Define testing", "font_size": 10.5, "is_bold": True},
            {"id": 8, "page": 5, "type": "text", "text": "Long Answer Questions", "font_size": 13, "is_bold": True},
            {"id": 9, "page": 5, "type": "text", "text": "Q1. Explain testing", "font_size": 10.5, "is_bold": True},
            {"id": 10, "page": 5, "type": "text", "text": "Q2. Choose the sample", "font_size": 10.5, "is_bold": True},
            {"id": 11, "page": 6, "type": "text", "text": "Unit 9: Correlation", "font_size": 20, "is_bold": True},
        ]
        classification = notes_ninja.local_classification(segments)
        self.assertEqual(classification["title_segment_id"], 1)
        self.assertEqual(classification["unit_headings"], [
            {"segment_id": 2, "unit_number": 8}, {"segment_id": 11, "unit_number": 9},
        ])
        self.assertEqual(classification["mcq_segment_ids"], [5])
        self.assertEqual(classification["qa_segment_ids"], [7, 9, 10])

    def test_fixed_components_are_selected_without_changing_item_text(self):
        document = {
            "title": "Statistics",
            "front_matter": [],
            "units": [{
                "unit_number": 8,
                "heading": "Unit 8: Testing",
                "content": [
                    {"type": "heading", "text": "Quick Revision Notes", "heading_level": "section"},
                    {"type": "paragraph", "text": "• Exact revision point", "preserve_lines": False},
                    {"type": "heading", "text": "Multiple Choice Questions", "heading_level": "section"},
                    {"type": "mcq", "question": "Q1. Exact question", "options": [], "answer": "A"},
                ],
            }],
        }
        formatted = notes_ninja.componentize_document(document)
        self.assertEqual(formatted["units"][0]["display_heading"], "Testing")
        self.assertEqual([block["type"] for block in formatted["units"][0]["blocks"]], ["summary", "mcq"])
        self.assertEqual(formatted["units"][0]["blocks"][0]["items"][0]["text"], "• Exact revision point")
        self.assertEqual(formatted["mcq_count"], 1)

    def test_decimal_continuation_is_not_classified_as_a_question(self):
        classification = notes_ninja.local_classification([
            {"id": 1, "page": 1, "type": "text", "text": "Study Notes", "font_size": 18, "is_bold": True},
            {"id": 2, "page": 1, "type": "text", "text": "Short Answer Questions", "font_size": 14, "is_bold": True},
            {"id": 3, "page": 1, "type": "text", "text": "0.01).", "font_size": 10.5, "is_bold": False},
            {"id": 4, "page": 1, "type": "text", "text": "1. Actual question?", "font_size": 10.5, "is_bold": True},
        ])
        self.assertEqual(classification["qa_segment_ids"], [4])

    def test_cover_uses_extracted_subject_and_formats_semester_units(self):
        self.assertEqual(notes_ninja._cover_title("OFFICE AUTOMATION TOOLS"), "Office Automation Tools")
        self.assertEqual(
            notes_ninja._cover_title("STATISTICS FOR MANAGERS THE STUDY SUPERPACK FULL STUDY (UNITS 8, 9, & 10)"),
            "Statistics for Managers",
        )
        self.assertEqual(
            notes_ninja._cover_subtitle(["BBA SEMESTER I", "FULL STUDY (UNITS 8, 9, 10 & 11):"]),
            "BBA · Semester 1 · Units 8, 9, 10 & 11",
        )

    def test_table_after_long_answer_is_not_swallowed_by_qa_grouping(self):
        document = notes_ninja.build_document(
            [
                {"id": 1, "page": 1, "type": "text", "text": "Study Notes"},
                {"id": 2, "page": 2, "type": "text", "text": "Long Answer Questions"},
                {"id": 3, "page": 2, "type": "text", "text": "Q1. Compare the tools"},
                {"id": 4, "page": 2, "type": "text", "text": "in detail.\nAnswer: Exact explanation"},
                {
                    "id": 5,
                    "page": 3,
                    "type": "table",
                    "headers": ["Tool", "Purpose"],
                    "rows": [["Writer", "Documents"]],
                },
                {"id": 6, "page": 3, "type": "text", "text": "Exact closing sentence"},
            ],
            {
                "title_segment_id": 1,
                "unit_headings": [],
                "heading_segment_ids": [2],
                "mcq_segment_ids": [],
                "qa_segment_ids": [3],
            },
        )
        items = document["units"][0]["content"]
        self.assertEqual([item["type"] for item in items], ["heading", "qa", "table", "paragraph"])
        self.assertEqual(items[1]["question"], "Q1. Compare the tools in detail.")
        self.assertEqual(items[1]["answer"], "Exact explanation")
        self.assertEqual(items[2]["rows"], [["Writer", "Documents"]])

    def test_separate_answer_heading_stays_with_each_long_question(self):
        segments = [
            {"id": 1, "page": 1, "type": "text", "text": "Study Notes", "font_size": 20, "is_bold": True},
            {"id": 2, "page": 2, "type": "text", "text": "Long Answer Questions", "font_size": 16, "is_bold": True},
            {"id": 3, "page": 2, "type": "text", "text": "1. Explain testing?", "font_size": 10.5},
            {"id": 4, "page": 2, "type": "text", "text": "Answer", "font_size": 16, "is_bold": True, "docling_label": "section_header"},
            {"id": 5, "page": 2, "type": "text", "text": "First exact answer.", "font_size": 10.5},
            {"id": 6, "page": 2, "type": "text", "text": "2. Explain correlation?", "font_size": 10.5},
            {"id": 7, "page": 2, "type": "text", "text": "Answer", "font_size": 16, "is_bold": True, "docling_label": "section_header"},
            {"id": 8, "page": 2, "type": "text", "text": "Second exact answer.", "font_size": 10.5},
        ]
        classification = notes_ninja.local_classification(segments)
        document = notes_ninja.build_document(segments, classification)
        questions = [item for item in document["units"][0]["content"] if item["type"] == "qa"]
        self.assertEqual([item["answer"] for item in questions], ["First exact answer.", "Second exact answer."])

    def test_numbered_list_item_can_be_first_mcq(self):
        classification = notes_ninja.local_classification([
            {"id": 1, "page": 1, "type": "text", "text": "Study Notes", "font_size": 20, "is_bold": True},
            {"id": 2, "page": 2, "type": "text", "text": "Multiple Choice Questions", "font_size": 16, "is_bold": True},
            {"id": 3, "page": 2, "type": "text", "text": "1. First exact question?", "font_size": 10.5, "source_list": True},
        ])
        self.assertEqual(classification["mcq_segment_ids"], [3])


if __name__ == "__main__":
    unittest.main()
