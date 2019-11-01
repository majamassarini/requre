import os
import tempfile

from requre.helpers.files import StoreFiles
from requre.storage import PersistentObjectStorage
from tests.testbase import BaseClass
import tarfile
from io import BytesIO
from tests.test_function_output import StoreFunctionOutput


class Base(BaseClass):
    @StoreFiles.arg_references({"target_file": 2})
    def create_file_content(self, value, target_file):
        with open(target_file, "w") as fd:
            fd.write(value)
        return "value"

    @StoreFiles.arg_references({"target_dir": 2})
    def create_dir_content(self, filename, target_dir, content="empty"):
        with open(os.path.join(target_dir, filename), "w") as fd:
            fd.write(content)


class FileStorage(Base):
    def test_base(self):
        """
        verify if tar archive is in persistent storage
        """
        filename = "some_random_name"
        self.create_temp_dir()
        self.create_dir_content(
            filename=filename, target_dir=self.temp_dir, content="ciao"
        )
        tar_data = PersistentObjectStorage().storage_object["X"]["file"]["tar"][
            "StoreFiles"
        ]["storage_test.yaml"]["target_dir"][0]["output"]
        with BytesIO(tar_data) as tar_byte:
            with tarfile.open(mode="r:xz", fileobj=tar_byte) as tar_archive:
                self.assertIn(filename, [x.name for x in tar_archive.getmembers()][-1])

    def test_create_file_content(self):
        """
        test if is able store files via decorated function create_file_content
        """
        self.create_temp_file()
        self.assertEqual(
            "value", self.create_file_content("ahoj", target_file=self.temp_file)
        )

        self.create_file_content("cao", target_file=self.temp_file)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False

        self.create_file_content("first", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        self.create_file_content("second", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        self.assertRaises(
            Exception, self.create_file_content, "third", target_file=self.temp_file
        )

    def test_create_file_content_positional(self):
        """
        Similar to  test_create_file_content,
        but test it also via positional parameters and mixing them
        """
        self.create_temp_file()
        self.create_file_content("ahoj", self.temp_file)
        self.create_file_content("cao", self.temp_file)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False

        self.create_temp_file()
        self.create_file_content("first", self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        # mix with positional option

        self.create_temp_file()
        self.create_file_content("second", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        self.create_temp_file()
        self.assertRaises(
            Exception, self.create_file_content, "third", target_file=self.temp_file
        )

    def test_create_dir_content(self):
        """
        Check if properly store and restore directory content
        """
        self.create_temp_dir()
        self.create_dir_content(
            filename="ahoj", target_dir=self.temp_dir, content="ciao"
        )
        self.assertIn("ahoj", os.listdir(self.temp_dir))
        with open(os.path.join(self.temp_dir, "ahoj"), "r") as fd:
            content = fd.read()
            self.assertIn("ciao", content)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False

        self.create_temp_dir()
        self.create_dir_content(
            filename="nonsense", target_dir=self.temp_dir, content="bad"
        )
        self.assertIn("ahoj", os.listdir(self.temp_dir))
        self.assertNotIn("nonsense", os.listdir(self.temp_dir))
        with open(os.path.join(self.temp_dir, "ahoj"), "r") as fd:
            content = fd.read()
            self.assertIn("ciao", content)
            self.assertNotIn("bad", content)

    def test_hidden_file(self):
        """
        Check if properly store and restore directory content with hidden file
        """
        filename = ".git"
        self.create_temp_dir()
        self.create_dir_content(
            filename=filename, target_dir=self.temp_dir, content="hidden"
        )

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False

        self.create_temp_dir()
        self.create_dir_content(
            filename="nonsense", target_dir=self.temp_dir, content="bad"
        )
        self.assertIn(filename, os.listdir(self.temp_dir))
        self.assertNotIn("nonsense", os.listdir(self.temp_dir))
        with open(os.path.join(self.temp_dir, filename), "r") as fd:
            content = fd.read()
            self.assertIn("hidden", content)
            self.assertNotIn("bad", content)


class SessionRecordingWithFileStore(Base):
    @StoreFiles.arg_references({"target_file": 2})
    def create_file_content(self, value, target_file):
        StoreFunctionOutput.run_command_wrapper(
            cmd=["bash", "-c", f"echo {value} > {target_file}"]
        )
        with open(target_file, "w") as fd:
            fd.write(value)

    def test(self):
        """
        Mixing command wrapper with file storage
        """
        self.create_temp_file()
        self.create_file_content("ahoj", target_file=self.temp_file)
        self.create_file_content("cao", target_file=self.temp_file)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False

        before = str(PersistentObjectStorage().storage_object)

        self.create_file_content("ahoj", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        self.create_file_content("cao", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        after = str(PersistentObjectStorage().storage_object)
        self.assertGreater(len(before), len(after))
        self.assertIn("True", before)


class DynamicFileStorage(Base):
    @StoreFiles.guess_args
    def create_file(self, value, target_file):
        with open(target_file, "w") as fd:
            fd.write(value)

    def test_create_file(self):
        """
        File storage where it try to guess what to store, based on *args and **kwargs values
        """
        self.create_temp_file()
        self.create_file("ahoj", self.temp_file)
        self.create_file("cao", self.temp_file)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        self.create_temp_file()
        self.create_file("first", self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        # mix with positional option

        self.create_temp_file()
        self.create_file("second", self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        self.create_temp_file()
        self.assertRaises(
            Exception, self.create_file_content, "third", target_file=self.temp_file
        )


class StoreOutputFile(Base):
    @StoreFiles.return_value
    def create_file(self, value):
        tmpfile = tempfile.mktemp()
        with open(tmpfile, "w") as fd:
            fd.write(value)
        return tmpfile

    def test_create_file(self):
        """
        Test File storage if file name is return value of function
        """
        ofile1 = self.create_file("ahoj")
        ofile2 = self.create_file("cao")

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False

        oofile1 = self.create_file("first")
        with open(ofile1, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        with open(oofile1, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        # mix with positional option

        oofile2 = self.create_file("second")
        with open(oofile2, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        self.assertEqual(ofile2, oofile2)
