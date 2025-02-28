# -*- coding: utf-8 -*-
"""Tests for writing ISA assay files"""


import filecmp
import os
import pytest

from altamisa.exceptions import (
    AdvisoryIsaValidationWarning,
    IsaWarning,
    ModerateIsaValidationWarning,
    ParseIsatabWarning,
)
from altamisa.isatab import (
    InvestigationReader,
    InvestigationValidator,
    AssayReader,
    AssayValidator,
    AssayWriter,
)
from .conftest import sort_file


# Helper to load, write and compare assays
def _parse_write_assert_assay(investigation_file, tmp_path, quote=None, normalize=False, skip=None):
    # Load investigation
    investigation = InvestigationReader.from_stream(investigation_file).read()
    InvestigationValidator(investigation).validate()
    directory = os.path.normpath(os.path.dirname(investigation_file.name))
    # Iterate assays
    for s, study_info in enumerate(investigation.studies):
        for a, assay_info in enumerate(study_info.assays):
            if skip and str(assay_info.path) in skip:
                continue
            # Load assay
            path_in = os.path.join(directory, assay_info.path)
            with open(path_in, "rt") as inputf:
                assay = AssayReader.from_stream(
                    "S{}".format(s + 1), "A{}".format(a + 1), inputf
                ).read()
            AssayValidator(investigation, study_info, assay_info, assay).validate()
            # Write assay to temporary file
            path_out = tmp_path / assay_info.path
            with open(path_out, "wt", newline="") as file:
                AssayWriter.from_stream(assay, file, quote=quote).write()
            if normalize:
                # Read and write assay again
                path_in = path_out
                with open(path_out, "rt") as inputf:
                    assay = AssayReader.from_stream(
                        "S{}".format(s + 1), "A{}".format(a + 1), inputf
                    ).read()
                AssayValidator(investigation, study_info, assay_info, assay).validate()
                path_out = tmp_path / (assay_info.path.name + "_b")
                with open(path_out, "wt", newline="") as file:
                    AssayWriter.from_stream(assay, file, quote=quote).write()
            # Sort and compare input and output
            path_in_s = tmp_path / (assay_info.path.name + ".in.sorted")
            path_out_s = tmp_path / (assay_info.path.name + ".out.sorted")
            assert filecmp.cmp(
                sort_file(path_in, path_in_s), sort_file(path_out, path_out_s), shallow=False
            )


def test_assay_writer_minimal_assay(minimal_investigation_file, tmp_path):
    with pytest.warns(IsaWarning) as record:
        _parse_write_assert_assay(minimal_investigation_file, tmp_path)
    # Check warnings
    assert 1 == len(record)


def test_assay_writer_minimal2_assay(minimal2_investigation_file, tmp_path):
    with pytest.warns(IsaWarning) as record:
        _parse_write_assert_assay(minimal2_investigation_file, tmp_path)
    # Check warnings
    assert 1 == len(record)


def test_assay_writer_small_assay(small_investigation_file, tmp_path):
    with pytest.warns(IsaWarning) as record:
        _parse_write_assert_assay(small_investigation_file, tmp_path)

    # Check warnings
    assert 2 == len(record)
    msg = (
        "Assay without platform:\nPath:\ta_small.txt"
        "\nMeasurement Type:\texome sequencing assay"
        "\nTechnology Type:\tnucleotide sequencing"
        "\nTechnology Platform:\t"
    )
    assert record[0].category == AdvisoryIsaValidationWarning
    assert str(record[0].message) == msg
    msg = (
        "Can't validate parameter values and names for process with undeclared protocol "
        '"Unknown" and name type "Data Transformation Name"'
    )
    assert record[1].category == ModerateIsaValidationWarning
    assert str(record[1].message) == msg


def test_assay_writer_small2_assay(small2_investigation_file, tmp_path):
    _parse_write_assert_assay(small2_investigation_file, tmp_path, normalize=True)


def test_assay_writer_BII_I_1(BII_I_1_investigation_file, tmp_path):
    # skipping proteome assay, because it's missing a lot of splits and pools
    with pytest.warns(IsaWarning) as record:
        _parse_write_assert_assay(
            BII_I_1_investigation_file, tmp_path, quote='"', skip=["a_proteome.txt"]
        )

    # Check warnings
    # investigation
    records_skip_ontology = 1
    # a_metabolome + a_microarray + a_transcriptome
    records_ms_assay_name = 111 + 0 + 0
    records_scan_name = 0 + 14 + 48
    records_normalization_name = 0 + 0 + 1
    records_data_transformation_name = 0 + 1 + 0
    assert (
        records_skip_ontology
        + records_ms_assay_name
        + records_scan_name
        + records_normalization_name
        + records_data_transformation_name
        == len(record)
    )

    msg = "Skipping empty ontology source: , , , "
    assert record[0].category == ParseIsatabWarning
    assert str(record[0].message) == msg

    msg = (
        "Can't validate parameter values and names for process with undeclared protocol "
        '"Unknown" and name type "MS Assay Name"'
    )
    assert record[1].category == ModerateIsaValidationWarning
    assert str(record[1].message) == msg

    msg = (
        "Can't validate parameter values and names for process with undeclared protocol "
        '"Unknown" and name type "Scan Name"'
    )
    assert record[112].category == ModerateIsaValidationWarning
    assert str(record[112].message) == msg

    msg = (
        "Can't validate parameter values and names for process with undeclared protocol "
        '"Unknown" and name type "Normalization Name"'
    )
    assert record[113].category == ModerateIsaValidationWarning
    assert str(record[113].message) == msg

    msg = (
        "Can't validate parameter values and names for process with undeclared protocol "
        '"Unknown" and name type "Data Transformation Name"'
    )
    assert record[162].category == ModerateIsaValidationWarning
    assert str(record[162].message) == msg


def test_assay_writer_gelelect(gelelect_investigation_file, tmp_path):
    with pytest.warns(IsaWarning) as record:
        _parse_write_assert_assay(gelelect_investigation_file, tmp_path, quote='"')
    # Check warnings
    assert 4 == len(record)
    msg = "Skipping empty ontology source: , , , "
    assert record[0].category == ParseIsatabWarning
    assert str(record[0].message) == msg
    msg = "Study without title:\nID:\tstudy01\nTitle:\t\nPath:\ts_study01.txt"
    assert record[1].category == ModerateIsaValidationWarning
    assert str(record[1].message) == msg
    msg = '"Normalization Name" not supported by protocol type "normalization" (only "data normalization")'
    assert record[2].category == ModerateIsaValidationWarning
    assert str(record[2].message) == msg
    assert record[3].category == ModerateIsaValidationWarning
    assert str(record[3].message) == msg
