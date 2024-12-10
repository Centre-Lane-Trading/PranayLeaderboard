import polars as pl

from datetime import datetime


class Leaderboard():
    def __init__(self):
        self.original = pl.read_json("leaderboard_example.json")
        self.window = pl.read_json("leaderboard_example.json")
        self.exclusions_df = pl.read_json("leaderboard_example.json")

        self.metric = "PnL"
        self.area_only = False
        self.grouping = True
        self.topn = None # group all nodes
        self.chart_type = "profit_total"
        self.window_start = datetime(2024, 9, 16)
        self.window_end = datetime(2024, 10, 15)

    def get_date_range(self):
        # Check if the 'date' column is already a date type, if so, use it directly
        
        date_column = self.original["date"]
        dates = date_column.to_list()
        return min(dates), max(dates)  # Return min and max dates as a tuple

    
    def which_df(self):
        """
        Depending on the state of the app, we focus on one dataframe or the other
        """
        if self.area_only:
            df = self.window
        else:
            df = self.exclusions_df

        return df

    def summarize(self):
        """
        Produces a summary leaderboard of the dataframe in focus
        """
        df = self.which_df()

        if self.grouping and self.topn is not None:
            # TODO: maybe we want to save these for the user to know which are
            #       the nodes included in the top for each policy
            topn = self.filter_topn()
            df = df.join(topn, on=["policy", "node"], how="inner") # always on policy AND node

        grouping_feats = self.which_grouping()
        summary = df.group_by(grouping_feats).agg(pl.col("*").sum())\
            .with_columns(
                (pl.col("profit_total")/pl.col("mwh_total")).alias("per MWh"),
                (pl.col("win_count_long")+pl.col("win_count_short")).alias("win_count"),
            )\
            .with_columns(
                (100*pl.col("win_count")/pl.col("mwh_total")).alias("win %")
            )\
            .select(
                *grouping_feats, # all the grouping variables should display
                pl.col("profit_total").alias("PnL"),
                "per MWh",
                "win %"
            )\
            .sort(by=self.metric, descending=True)

        return summary

    def which_grouping(self):
        # keep policies separate always; node separation is optional (user input)
        grouping = ["policy"]
        if self.grouping == False:
            grouping.append("node")

        return grouping

    def filter_topn(self):
        df = self.which_df()

        grouping_feats = ["policy", "node"] # the topn filter is always on policy AND node
        topn = df.group_by(grouping_feats).agg(pl.col("*").sum())\
            .with_columns(
                (pl.col("profit_total")/pl.col("mwh_total")).alias("per MWh"),
                (pl.col("win_count_long")+pl.col("win_count_short")).alias("win_count"),
            )\
            .with_columns(
                (100*pl.col("win_count")/pl.col("mwh_total")).alias("win %")
            )\
            .select(
                *grouping_feats,
                pl.col("profit_total").alias("PnL"),
                "per MWh",
                "win %"
            )\
            .sort(by=self.metric, descending=True)\
            .group_by("policy")\
            .head(self.topn)\
            .select(["policy", "node"]) # unclear whether this should always equal grouping

        return topn

    def exclude_region(self, start_date, end_date):
        """
        Excluding a region modifies the exclusions dataframe, which in turn modifies the window

        Event: selection (i.e. exclusion), on mouse release
        """
        self.exclusions_df = self.exclusions_df.filter(
            ~pl.col("date").is_between(start_date, end_date)
        )
        self.window = self.exclusions_df.filter(
            pl.col("date").is_between(self.window_start, self.window_end)
        )

    def zoom_in(self, start_date, end_date):
        """
        Zooming in modifies the window

        Event: zoom-in, on mouse release
        """
        self.window_start = start_date
        self.window_end = end_date
        self.window = self.exclusions_df.filter(
            pl.col("date").is_between(self.window_start, self.window_end))

    def pan(self, start_date, end_date):
        """
        Panning is the same as zooming-in, once the start_date and end_date dates are known

        Event: pan, on mouse release (alt. on mouse move)
        """
        self.zoom_in(start_date, end_date)

    def toggle(self):
        """
        Toggles the area-only value from False to True and viceversa

        Event: button, on click
        """
        self.area_only = not self.area_only

    def group(self):
        """
        Toggles the grouping value from False to True and viceversa

        Event: button, on click
        """
        self.grouping = not self.grouping

    def set_topn(self, n):
        """
        Overwrites the topn value

        Event: button, on click (should be disabled if grouping is False)
        """
        self.topn = n

    def set_metric(self, new_metric):
        """
        Changes the value of the metric to sort-by

        Valid metrics are 'PnL', 'Per MWh', 'win %'

        Event: button, on click
        """
        # TODO: validate new metric
        self.metric = new_metric
