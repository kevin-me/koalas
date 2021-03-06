#
# Copyright (C) 2019 Databricks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import pandas as pd

from databricks import koalas as ks
from databricks.koalas.config import set_option, reset_option
from databricks.koalas.testing.utils import ReusedSQLTestCase, SQLTestUtils


class OpsOnDiffFramesGroupByTest(ReusedSQLTestCase, SQLTestUtils):
    @classmethod
    def setUpClass(cls):
        super(OpsOnDiffFramesGroupByTest, cls).setUpClass()
        set_option("compute.ops_on_diff_frames", True)

    @classmethod
    def tearDownClass(cls):
        reset_option("compute.ops_on_diff_frames")
        super(OpsOnDiffFramesGroupByTest, cls).tearDownClass()

    def test_groupby_different_lengths(self):
        pdfs1 = [
            pd.DataFrame({"c": [4, 2, 7, 3, None, 1, 1, 1, 2], "d": list("abcdefght")}),
            pd.DataFrame({"c": [4, 2, 7, None, 1, 1, 2], "d": list("abcdefg")}),
            pd.DataFrame({"c": [4, 2, 7, 3, None, 1, 1, 1, 2, 2], "d": list("abcdefghti")}),
        ]
        pdfs2 = [
            pd.DataFrame({"a": [1, 2, 6, 4, 4, 6, 4, 3, 7], "b": [4, 2, 7, 3, 3, 1, 1, 1, 2]}),
            pd.DataFrame({"a": [1, 2, 6, 4, 4, 6, 4, 7], "b": [4, 2, 7, 3, 3, 1, 1, 2]}),
            pd.DataFrame({"a": [1, 2, 6, 4, 4, 6, 4, 3, 7], "b": [4, 2, 7, 3, 3, 1, 1, 1, 2]}),
        ]

        for pdf1, pdf2 in zip(pdfs1, pdfs2):
            kdf1 = ks.from_pandas(pdf1)
            kdf2 = ks.from_pandas(pdf2)

            for as_index in [True, False]:
                if as_index:
                    sort = lambda df: df.sort_index()
                else:
                    sort = lambda df: df.sort_values("c").reset_index(drop=True)
                self.assert_eq(
                    sort(kdf1.groupby(kdf2.a, as_index=as_index).sum()),
                    sort(pdf1.groupby(pdf2.a, as_index=as_index).sum()),
                )

                self.assert_eq(
                    sort(kdf1.groupby(kdf2.a, as_index=as_index).c.sum()),
                    sort(pdf1.groupby(pdf2.a, as_index=as_index).c.sum()),
                )
                self.assert_eq(
                    sort(kdf1.groupby(kdf2.a, as_index=as_index)["c"].sum()),
                    sort(pdf1.groupby(pdf2.a, as_index=as_index)["c"].sum()),
                )

    def test_groupby_multiindex_columns(self):
        pdf1 = pd.DataFrame(
            {("y", "c"): [4, 2, 7, 3, None, 1, 1, 1, 2], ("z", "d"): list("abcdefght"),}
        )
        pdf2 = pd.DataFrame(
            {("x", "a"): [1, 2, 6, 4, 4, 6, 4, 3, 7], ("x", "b"): [4, 2, 7, 3, 3, 1, 1, 1, 2],}
        )
        kdf1 = ks.from_pandas(pdf1)
        kdf2 = ks.from_pandas(pdf2)

        self.assert_eq(
            kdf1.groupby(kdf2[("x", "a")]).sum().sort_index(),
            pdf1.groupby(pdf2[("x", "a")]).sum().sort_index(),
        )

        self.assert_eq(
            kdf1.groupby(kdf2[("x", "a")], as_index=False)
            .sum()
            .sort_values(("y", "c"))
            .reset_index(drop=True),
            pdf1.groupby(pdf2[("x", "a")], as_index=False)
            .sum()
            .sort_values(("y", "c"))
            .reset_index(drop=True),
        )
        self.assert_eq(
            kdf1.groupby(kdf2[("x", "a")])[[("y", "c")]].sum().sort_index(),
            pdf1.groupby(pdf2[("x", "a")])[[("y", "c")]].sum().sort_index(),
        )

    def test_split_apply_combine_on_series(self):
        pdf1 = pd.DataFrame({"C": [0.362, 0.227, 1.267, -0.562], "B": [1, 2, 3, 4]})
        pdf2 = pd.DataFrame({"A": [1, 1, 2, 2]})
        kdf1 = ks.from_pandas(pdf1)
        kdf2 = ks.from_pandas(pdf2)

        for as_index in [True, False]:
            if as_index:
                sort = lambda df: df.sort_index()
            else:
                sort = lambda df: df.sort_values(list(df.columns)).reset_index(drop=True)

            with self.subTest(as_index=as_index):
                self.assert_eq(
                    sort(kdf1.groupby(kdf2.A, as_index=as_index).sum()),
                    sort(pdf1.groupby(pdf2.A, as_index=as_index).sum()),
                )
                self.assert_eq(
                    sort(kdf1.groupby(kdf2.A, as_index=as_index).B.sum()),
                    sort(pdf1.groupby(pdf2.A, as_index=as_index).B.sum()),
                )

        self.assert_eq(
            kdf1.B.groupby(kdf2.A).sum().sort_index(), pdf1.B.groupby(pdf2.A).sum().sort_index(),
        )
        self.assert_eq(
            (kdf1.B + 1).groupby(kdf2.A).sum().sort_index(),
            (pdf1.B + 1).groupby(pdf2.A).sum().sort_index(),
        )

    def test_aggregate(self):
        pdf1 = pd.DataFrame({"C": [0.362, 0.227, 1.267, -0.562], "B": [1, 2, 3, 4]})
        pdf2 = pd.DataFrame({"A": [1, 1, 2, 2]})
        kdf1 = ks.from_pandas(pdf1)
        kdf2 = ks.from_pandas(pdf2)

        for as_index in [True, False]:
            if as_index:
                sort = lambda df: df.sort_index()
            else:
                sort = lambda df: df.sort_values(list(df.columns)).reset_index(drop=True)

            with self.subTest(as_index=as_index):
                self.assert_eq(
                    sort(kdf1.groupby(kdf2.A, as_index=as_index).agg("sum")),
                    sort(pdf1.groupby(pdf2.A, as_index=as_index).agg("sum")),
                )
                self.assert_eq(
                    sort(kdf1.groupby(kdf2.A, as_index=as_index).agg({"B": "min", "C": "sum"})),
                    sort(pdf1.groupby(pdf2.A, as_index=as_index).agg({"B": "min", "C": "sum"})),
                )
                self.assert_eq(
                    sort(
                        kdf1.groupby(kdf2.A, as_index=as_index).agg(
                            {"B": ["min", "max"], "C": "sum"}
                        )
                    ),
                    sort(
                        pdf1.groupby(pdf2.A, as_index=as_index).agg(
                            {"B": ["min", "max"], "C": "sum"}
                        )
                    ),
                )

        # multi-index columns
        columns = pd.MultiIndex.from_tuples([("Y", "C"), ("X", "B")])
        pdf1.columns = columns
        kdf1.columns = columns

        columns = pd.MultiIndex.from_tuples([("X", "A")])
        pdf2.columns = columns
        kdf2.columns = columns

        for as_index in [True, False]:
            stats_kdf = kdf1.groupby(kdf2[("X", "A")], as_index=as_index).agg(
                {("X", "B"): "min", ("Y", "C"): "sum"}
            )
            stats_pdf = pdf1.groupby(pdf2[("X", "A")], as_index=as_index).agg(
                {("X", "B"): "min", ("Y", "C"): "sum"}
            )
            self.assert_eq(
                stats_kdf.sort_values(by=[("X", "B"), ("Y", "C")]).reset_index(drop=True),
                stats_pdf.sort_values(by=[("X", "B"), ("Y", "C")]).reset_index(drop=True),
            )

        stats_kdf = kdf1.groupby(kdf2[("X", "A")]).agg(
            {("X", "B"): ["min", "max"], ("Y", "C"): "sum"}
        )
        stats_pdf = pdf1.groupby(pdf2[("X", "A")]).agg(
            {("X", "B"): ["min", "max"], ("Y", "C"): "sum"}
        )
        self.assert_eq(
            stats_kdf.sort_values(
                by=[("X", "B", "min"), ("X", "B", "max"), ("Y", "C", "sum")]
            ).reset_index(drop=True),
            stats_pdf.sort_values(
                by=[("X", "B", "min"), ("X", "B", "max"), ("Y", "C", "sum")]
            ).reset_index(drop=True),
        )

    def test_duplicated_labels(self):
        pdf1 = pd.DataFrame({"A": [3, 2, 1]})
        pdf2 = pd.DataFrame({"A": [1, 2, 3]})
        kdf1 = ks.from_pandas(pdf1)
        kdf2 = ks.from_pandas(pdf2)

        self.assert_eq(
            kdf1.groupby(kdf2.A).sum().sort_index(), pdf1.groupby(pdf2.A).sum().sort_index()
        )
        self.assert_eq(
            kdf1.groupby(kdf2.A, as_index=False).sum().sort_values("A").reset_index(drop=True),
            pdf1.groupby(pdf2.A, as_index=False).sum().sort_values("A").reset_index(drop=True),
        )
