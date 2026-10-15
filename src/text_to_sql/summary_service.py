import pandas as pd


def summarize_result(question: str, result: pd.DataFrame) -> str:
    """Generate a simple, rule-based summary of SQL query results."""

    if result.empty:
        return "No results were found for your question."

    columns = {column.lower(): column for column in result.columns}

    # Handle revenue rankings.
    if "delivered_revenue" in columns:
        revenue_col = columns["delivered_revenue"]

        location_col = next(
            (
                columns[name]
                for name in ["restaurant_city", "restaurant_name", "city"]
                if name in columns
            ),
            None,
        )

        if location_col:
            top_row = result.iloc[0]
            name = str(top_row[location_col])
            revenue = float(top_row[revenue_col])

            summary = (
                f"The top result is {name}, with delivered revenue "
                f"of ₹{revenue:,.2f}."
            )

            if len(result) > 1:
                second_row = result.iloc[1]
                second_name = str(second_row[location_col])
                second_revenue = float(second_row[revenue_col])

                summary += (
                    f" In second place is {second_name}, with "
                    f"₹{second_revenue:,.2f}."
                )

            summary += (
                f" The query returned {len(result)} results in total."
            )

            return summary

    # Handle count queries.
    if len(result) == 1 and len(result.columns) == 1:
        column = result.columns[0]
        value = result.iloc[0, 0]
        label = column.replace("_", " ")

        if pd.api.types.is_number(value):
            if isinstance(value, float) and value.is_integer():
                value = int(value)

            return f"The result is {value:,} for {label}."

        return f"The result for {label} is {value}."

    # General fallback for other queries.
    return (
        f"Your query returned {len(result):,} rows "
        f"across {len(result.columns)} columns."
    )