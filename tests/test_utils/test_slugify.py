"""Unit tests for the slugify utility."""

from app.utils.slugify import slugify, slugify_filename


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_characters(self):
        assert slugify("foo@bar!baz") == "foo-bar-baz"

    def test_consecutive_hyphens(self):
        assert slugify("a---b") == "a-b"

    def test_unicode(self):
        assert slugify("café résumé") == "cafe-resume"

    def test_empty(self):
        assert slugify("") == ""


class TestSlugifyFilename:
    def test_simple(self):
        assert slugify_filename("photo.png") == "photo.png"

    def test_spaces_and_parens(self):
        assert (
            slugify_filename("My Vacation Photo (2).PNG") == "my-vacation-photo-2.png"
        )

    def test_preserves_extension(self):
        assert slugify_filename("IMAGE.JPEG") == "image.jpeg"

    def test_empty_stem_becomes_untitled(self):
        assert slugify_filename(".png") == "untitled.png"

    def test_no_extension(self):
        assert slugify_filename("readme") == "readme"
