"""Matplotlib charts. Percentages only: no rupee amounts anywhere (v1 rule)."""
import matplotlib

matplotlib.use("Agg")  # draw to memory, no window needed (works in the browser build too)
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from .lots import ORDER

BG, DARK, ACCENT, INDIA, MUTED = "#FAFAF7", "#1A1A1A", "#C0392B", "#2C5F8A", "#888888"
PANEL, STRIP = "#EFEFE8", "#DCDCD3"
SERIF = "serif"


def _strip(ax, text, side="top"):
    """Grey label band above a panel (bucket) or on its right (metric)."""
    if side == "top":
        ax.add_patch(mpatches.Rectangle((0, 1.0), 1, 0.11, transform=ax.transAxes, clip_on=False, fc=STRIP, ec="none"))
        ax.text(0.5, 1.055, text, transform=ax.transAxes, ha="center", va="center", fontsize=10, color=DARK, family=SERIF)
    else:
        ax.add_patch(mpatches.Rectangle((1.0, 0), 0.09, 1, transform=ax.transAxes, clip_on=False, fc=STRIP, ec="none"))
        ax.text(1.045, 0.5, text, transform=ax.transAxes, ha="center", va="center", rotation=270, fontsize=10, color=DARK, family=SERIF)


def wins(t):
    """Buckets where your funds are ahead: XIRR for 1Y+, absolute return for <1Y."""
    return sum(
        (r["my_abs_%"] > r["nifty_abs_%"]) if b == "<1Y" else (r["xirr_gap_%"] > 0)
        for b, r in t.iterrows()
    )


def facet_title(t, label):
    n = wins(t)
    if n == 0:
        return f"{label} did not beat the Nifty 50 in any of {len(t)} buckets"
    return f"{label} beat the Nifty 50 in {n} of {len(t)} buckets"


def facet_chart(t, label, as_of):
    """Columns = buckets, top row = XIRR, bottom row = absolute return."""
    t = t.reindex([b for b in ORDER if b in t.index])
    rows = [("my_xirr_%", "nifty_xirr_%", "XIRR (% a year)"),
            ("my_abs_%", "nifty_abs_%", "Absolute return (%)")]
    with plt.rc_context({"font.family": SERIF}):
        fig, axes = plt.subplots(2, len(t), figsize=(3 * len(t) + 1.5, 6.5), sharey="row", squeeze=False)
        fig.patch.set_facecolor(BG)
        for r, (mine_col, nifty_col, metric) in enumerate(rows):
            for c, (bucket, row) in enumerate(t.iterrows()):
                ax = axes[r, c]
                ax.set_facecolor(PANEL)
                # XIRR under a year is annualised from a few months, so fade it
                fade = 0.35 if (bucket == "<1Y" and r == 0) else 1.0
                for x, v, colour in zip([0, 1], [row[mine_col], row[nifty_col]], [ACCENT, INDIA]):
                    if v != v:  # NaN: nothing to draw
                        continue
                    ax.bar(x, v, 0.6, color=colour, alpha=fade)
                    ax.text(x, v, f"{v:.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5,
                            color=colour, fontweight="bold" if colour == ACCENT else "normal", alpha=max(fade, 0.6))
                ax.axhline(0, color=DARK, lw=0.8)
                ax.grid(axis="y", color=BG, lw=1.0)
                ax.set_axisbelow(True)
                for side in ["top", "right", "left", "bottom"]:
                    ax.spines[side].set_visible(False)
                ax.tick_params(length=0, colors=DARK, labelsize=9)
                ax.set_xlim(-0.6, 1.6)
                ax.set_xticks([0, 1], ["My funds", "Nifty 50"] if r == 1 else ["", ""])
                ax.margins(y=0.2)
                if r == 0:
                    _strip(ax, bucket, "top")
                    if fade < 1:
                        ax.text(0.5, 0.97, "faded: under a year,\nread abs %", transform=ax.transAxes,
                                ha="center", va="top", fontsize=7.5, color=MUTED)
                if c == len(t) - 1:
                    _strip(ax, metric, "right")
        fig.suptitle(facet_title(t, label), x=0.04, ha="left", fontsize=13, fontweight="bold", color=DARK)
        fig.subplots_adjust(left=0.07, right=0.93, top=0.84, bottom=0.11, wspace=0.05, hspace=0.18)
        fig.text(0.04, 0.012, f"Fundprint · Nifty 50 = UTI Nifty 50 Index Fund Direct Growth, same dates & amounts · as of {as_of:%d %b %Y}",
                 fontsize=7.5, color=MUTED, ha="left")
    return fig


def allocation_chart(t):
    """Share of money invested in each bucket; the biggest bucket is highlighted."""
    t = t.reindex([b for b in ORDER if b in t.index])
    top = t["share_%"].idxmax()
    with plt.rc_context({"font.family": SERIF}):
        fig, ax = plt.subplots(figsize=(8, 3.2))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        labels = list(t.index)[::-1]  # oldest on top
        vals = [t.loc[b, "share_%"] for b in labels]
        ax.barh(labels, vals, 0.6, color=[ACCENT if b == top else "#BBBBBB" for b in labels])
        for y, (b, v) in enumerate(zip(labels, vals)):
            ax.text(v + 1, y, f"{v:.1f}%", va="center", fontsize=9, color=ACCENT if b == top else DARK)
        ax.set_xlim(0, max(vals) * 1.15)
        ax.set_xticks([])
        ax.tick_params(length=0, labelsize=10, colors=DARK)
        for s in ax.spines.values():
            s.set_visible(False)
        fig.suptitle(f"{top} holds {t.loc[top, 'share_%']:.0f}% of the money invested",
                     x=0.04, ha="left", fontsize=13, fontweight="bold", color=DARK)
        fig.text(0.04, 0.02, "Share of money invested in units still held, by time since purchase · Fundprint",
                 fontsize=7.5, color=MUTED, ha="left")
        fig.subplots_adjust(left=0.1, right=0.96, top=0.82, bottom=0.13)
    return fig
