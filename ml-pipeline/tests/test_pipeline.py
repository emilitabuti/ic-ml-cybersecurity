"""Testes da limpeza UNSW-NB15 usada pelo pipeline temporal."""
import numpy as np
import pandas as pd
import pytest

from src.data.pipeline.cleaner import (
    clean_column_names,
    remove_duplicate_columns,
    remove_duplicate_rows,
    treat_infinite_and_missing,
)


class TestCleanColumnNames:
    """Valida padronização de nomes de colunas para snake_case."""

    def test_strips_leading_trailing_spaces(self) -> None:
        df = pd.DataFrame({" Flow Duration ": [1, 2]})
        result = clean_column_names(df)
        assert "Flow_Duration" in result.columns

    def test_replaces_spaces_with_underscore(self) -> None:
        df = pd.DataFrame({"Flow Duration": [1]})
        result = clean_column_names(df)
        assert "Flow_Duration" in result.columns

    def test_replaces_slash_with_underscore(self) -> None:
        df = pd.DataFrame({"Flow/s": [1]})
        result = clean_column_names(df)
        assert "Flow_s" in result.columns

    def test_replaces_hyphen_with_underscore(self) -> None:
        df = pd.DataFrame({"Flow-Duration": [1]})
        result = clean_column_names(df)
        assert "Flow_Duration" in result.columns

    def test_preserves_already_clean_names(self) -> None:
        df = pd.DataFrame({"Binary_Label": [0, 1]})
        result = clean_column_names(df)
        assert "Binary_Label" in result.columns


class TestRemoveDuplicateColumns:
    """Valida remoção de colunas com sufixo 'duplicated'."""

    def test_removes_duplicated_suffix_column(self) -> None:
        df = pd.DataFrame({"a": [1], "b_duplicated": [2], "c": [3]})
        result = remove_duplicate_columns(df)
        assert "b_duplicated" not in result.columns

    def test_preserves_non_duplicated_columns(self) -> None:
        df = pd.DataFrame({"a": [1], "b_duplicated": [2], "c": [3]})
        result = remove_duplicate_columns(df)
        assert "a" in result.columns
        assert "c" in result.columns

    def test_no_change_when_no_duplicated_columns(self) -> None:
        df = pd.DataFrame({"a": [1], "b": [2]})
        result = remove_duplicate_columns(df)
        assert list(result.columns) == ["a", "b"]


class TestRemoveDuplicateRows:
    """Valida remoção de linhas duplicadas."""

    def test_removes_exact_duplicate_rows(self) -> None:
        df = pd.DataFrame({"a": [1, 1, 2], "b": [10, 10, 20]})
        result = remove_duplicate_rows(df)
        assert len(result) == 2

    def test_preserves_first_occurrence(self) -> None:
        df = pd.DataFrame({"a": [1, 1, 1], "b": [10, 10, 10]})
        result = remove_duplicate_rows(df)
        assert len(result) == 1

    def test_no_change_when_no_duplicates(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = remove_duplicate_rows(df)
        assert len(result) == 3


class TestTreatInfiniteAndMissing:
    """Valida substituição de inf/-inf e NaN por 0."""

    def test_replaces_positive_inf_with_zero(self) -> None:
        df = pd.DataFrame({"a": [1.0, float("inf"), 3.0]})
        result = treat_infinite_and_missing(df)
        assert result["a"].iloc[1] == 0.0

    def test_replaces_negative_inf_with_zero(self) -> None:
        df = pd.DataFrame({"a": [1.0, float("-inf"), 3.0]})
        result = treat_infinite_and_missing(df)
        assert result["a"].iloc[1] == 0.0

    def test_replaces_nan_with_zero(self) -> None:
        df = pd.DataFrame({"a": [1.0, float("nan"), 3.0]})
        result = treat_infinite_and_missing(df)
        assert result["a"].iloc[1] == 0.0

    def test_preserves_normal_values(self) -> None:
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        result = treat_infinite_and_missing(df)
        assert list(result["a"]) == [1.0, 2.0, 3.0]

    def test_does_not_mutate_original_dataframe(self) -> None:
        """Garante que inplace=False — o DataFrame original não é modificado."""
        df = pd.DataFrame({"a": [1.0, float("inf")]})
        original_val = df["a"].iloc[1]
        treat_infinite_and_missing(df)
        assert df["a"].iloc[1] == original_val


class TestCleanDatasetPaths:
    """Valida geração em caminho novo sem sobrescrita acidental."""

    def test_clean_unsw_writes_custom_output_without_mutating_input(
        self,
        tmp_path,
    ) -> None:
        from src.data.pipeline.cleaner import clean_unsw_nb15

        source = tmp_path / "unsw_raw.parquet"
        destination = tmp_path / "unsw_cleaned_temporal.parquet"
        original = pd.DataFrame(
            {
                "attack_cat": [None, "Fuzzers", "Fuzzers"],
                "label": [0, 1, 1],
                "is_ftp_login": [np.nan, 1.0, 1.0],
                "ct_flw_http_mthd": [np.nan, 2.0, 2.0],
                "source_file": ["part-0", "part-0", "part-0"],
                "stcpb": [10, 20, 20],
            }
        )
        original.to_parquet(source, index=False)

        result_path = clean_unsw_nb15(
            input_path=source,
            output_path=destination,
            overwrite=False,
        )

        result = pd.read_parquet(result_path)
        source_after = pd.read_parquet(source)
        assert result_path == destination
        assert len(result) == 2
        assert result["attack_cat"].tolist() == ["BENIGN", "Fuzzer"]
        assert result["Binary_Label"].tolist() == [0, 1]
        assert result["is_ftp_login"].tolist() == [0.0, 1.0]
        pd.testing.assert_frame_equal(source_after, original)

    def test_clean_unsw_refuses_existing_output_without_overwrite(
        self,
        tmp_path,
    ) -> None:
        from src.data.pipeline.cleaner import clean_unsw_nb15

        source = tmp_path / "unsw_raw.parquet"
        destination = tmp_path / "already_exists.parquet"
        pd.DataFrame(
            {
                "attack_cat": [None],
                "label": [0],
                "source_file": ["part-0"],
            }
        ).to_parquet(source, index=False)
        destination.write_bytes(b"do-not-overwrite")

        with pytest.raises(FileExistsError, match="já existe"):
            clean_unsw_nb15(
                input_path=source,
                output_path=destination,
                overwrite=False,
            )

        assert destination.read_bytes() == b"do-not-overwrite"
