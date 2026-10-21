import pandas as pd


def summarize_result(question: str, result: pd.DataFrame) -> str:
    """Generate readable, rule-based summaries of SQL query results."""

    if result.empty:
        return "No results were found for your question."

    columns = {column.lower(): column for column in result.columns}

    # Handle revenue rankings.
    revenue_col = next(
        (
            columns[name]
            for name in [
                "delivered_revenue",
                "total_revenue",
                "revenue",
                "total_delivered_revenue",
            ]
            if name in columns
        ),
        None,
    )

    if revenue_col:
        location_col = next(
            (
                columns[name]
                for name in [
                    "restaurant_name",
                    "restaurant_city",
                    "city",
                    "name",
                ]
                if name in columns
            ),
            None,
        )

        if location_col and len(result.columns) >= 2:
            lines = ["Here are the results, ranked by revenue:\n"]

            for position, (_, row) in enumerate(
                result.head(10).iterrows(), start=1
            ):
                name = str(row[location_col])
                revenue = pd.to_numeric(
                    row[revenue_col], errors="coerce"
                )

                if pd.notna(revenue):
                    lines.append(
                        f"{position}. {name}: ₹{revenue:,.2f}"
                    )

            lines.append(
                f"\nShowing {min(len(result), 10)} of "
                f"{len(result):,} results."
            )

            return "\n".join(lines)

    # Handle single-value results, including counts and percentages.
    if len(result) == 1 and len(result.columns) == 1:
        column = result.columns[0]
        value = result.iloc[0, 0]
        label = column.replace("_", " ")

        if pd.api.types.is_number(value):
            numeric_value = float(value)

            if any(
                term in column.lower()
                for term in ["rate", "percentage", "percent"]
            ):
                return f"The {label} is {numeric_value:,.2f}%."

            if "revenue" in column.lower():
                return f"The {label} is ₹{numeric_value:,.2f}."

            if numeric_value.is_integer():
                return f"The result is {int(numeric_value):,} for {label}."

            return f"The result is {numeric_value:,.2f} for {label}."

        return f"The result for {label} is {value}."

    # General fallback.
    return (
        f"Your query returned {len(result):,} rows "
        f"across {len(result.columns)} columns."
    )