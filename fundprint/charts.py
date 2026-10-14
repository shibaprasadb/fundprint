"""Matplotlib charts. Percentages only: no rupee amounts anywhere (v1 rule)."""
import matplotlib

matplotlib.use("Agg")  # draw to memory, no window needed (works in the browser build too)
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

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


# ---- Big picture charts ----

def _wrap(text, width):
    import textwrap
    return "\n".join(textwrap.fill(line, width) for line in text.split("\n"))


def _pp(v):
    return f"{v:+.1f} pp".replace("-", "−")


def gaps_chart(t):
    """One bar per equity fund: its gap to the Nifty 50 twin, in percentage points."""
    from matplotlib.transforms import blended_transform_factory
    from .insights import gaps_title

    n = len(t)
    with plt.rc_context({"font.family": SERIF}):
        fig, ax = plt.subplots(figsize=(8, 0.62 * n + 2.6))
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        ys = list(range(n))[::-1]   # most ahead on top
        span = max(t.gap_pp.abs().max(), 1.0) * 1.9
        ax.set_xlim(-span, span)
        ax.set_ylim(-0.6, n - 0.4)
        side = blended_transform_factory(ax.transAxes, ax.transData)
        for y, r in zip(ys, t.itertuples()):
            fade = 0.35 if r.young else 1.0
            ax.barh(y, r.gap_pp, 0.55, color=ACCENT, alpha=fade)
            ax.text(r.gap_pp + (span * 0.02) * (1 if r.gap_pp >= 0 else -1), y + (0.1 if r.young else 0),
                    _pp(r.gap_pp), va="center", ha="left" if r.gap_pp >= 0 else "right",
                    fontsize=9, color=ACCENT, fontweight="bold")
            if r.young:
                ax.text(r.gap_pp + (span * 0.02) * (1 if r.gap_pp >= 0 else -1), y - 0.17, "<1Y, absolute return",
                        va="center", ha="left" if r.gap_pp >= 0 else "right", fontsize=7, color=MUTED)
            name = r.name if len(r.name) <= 30 else r.name[:29].rstrip() + "…"
            ax.text(-0.02, y + 0.12, name, transform=side, ha="right", va="center", fontsize=9, color=DARK)
            ax.text(-0.02, y - 0.17, f"{r._2:.0f}% of equity money", transform=side, ha="right", va="center",
                    fontsize=7.5, color=MUTED)
        ax.axvline(0, color=DARK, lw=0.8)
        ax.set_yticks([])
        ax.set_xticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.text(0.5, -0.02 - 0.12 / max(n, 1), "◀ behind its twin        ahead of its twin ▶", transform=ax.transAxes,
                ha="center", va="top", fontsize=8, color=MUTED)

        sub = ("Each fund compared with a Nifty 50 index fund bought on the same dates, not with its own category. "
               "A midcap or small cap fund can trail the Nifty 50 simply because its whole category did.")
        h = 0.62 * n + 2.6
        fig.text(0.04, 1 - 0.25 / h, gaps_title(t), ha="left", va="top", fontsize=13, fontweight="bold", color=DARK)
        fig.text(0.04, 1 - 0.55 / h, "Equity funds only", ha="left", va="top", fontsize=8.5, color=MUTED)
        fig.text(0.04, 1 - 0.8 / h, _wrap(sub, 105), ha="left", va="top", fontsize=8.5, color=DARK)
        foot = "Gap in XIRR, percentage points · Fundprint · Nifty 50 = UTI Nifty 50 Index Fund Direct Growth"
        fig.text(0.04, 0.012, foot, fontsize=7.5, color=MUTED, ha="left")
        fig.subplots_adjust(left=0.36, right=0.96, top=1 - 1.55 / h, bottom=0.45 / h + 0.05)
    return fig


def periodicity_chart(pr, as_of):
    """Nifty 50 NAV over the years, with a dot for every purchase: periodic (filled) or one-off (hollow)."""
    from matplotlib.lines import Line2D
    from .insights import periodicity_subtitle, periodicity_title

    p = pr.purchases
    line = pr.levels[pr.levels.index >= p.date.min() - pd.Timedelta(days=45)]
    with plt.rc_context({"font.family": SERIF}):
        fig = plt.figure(figsize=(9, 6.6))
        fig.patch.set_facecolor(BG)
        ax = fig.add_axes([0.09, 0.2, 0.88, 0.5])
        ax.set_facecolor(BG)
        ax.plot(line.index, line.nav, color=DARK, lw=0.9)
        for periodic, g in p.groupby("periodic"):
            if periodic:
                ax.scatter(g.date, g.nav, s=28, color=ACCENT, alpha=0.5, linewidths=0, zorder=3)
            else:
                ax.scatter(g.date, g.nav, s=28, facecolors="none", edgecolors=MUTED, linewidths=0.9, zorder=3)
        ax.set_ylabel("Nifty 50 index fund NAV", color=DARK, fontsize=9)
        ax.tick_params(length=0, colors=DARK, labelsize=9)
        ax.grid(axis="y", color=PANEL, lw=1.0)
        ax.set_axisbelow(True)
        for s in ax.spines.values():
            s.set_visible(False)

        handles = [Line2D([], [], marker="o", ls="", color=ACCENT, alpha=0.6, ms=8, label="Periodic"),
                   Line2D([], [], marker="o", ls="", mfc="none", mec=MUTED, ms=8, label="One-off")]
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=len(handles),
                  frameon=False, fontsize=8, labelcolor=DARK, handletextpad=0.2, columnspacing=1.1)

        fig.text(0.04, 0.965, _wrap(periodicity_title(pr), 78), ha="left", va="top", fontsize=13,
                 fontweight="bold", color=DARK)
        fig.text(0.04, 0.925, "All funds", ha="left", va="top", fontsize=8.5, color=MUTED)
        fig.text(0.04, 0.89, periodicity_subtitle(pr), ha="left", va="top", fontsize=9, color=DARK, linespacing=1.5)
        fig.text(0.04, 0.012, f"Fundprint · Nifty 50 = UTI Nifty 50 Index Fund Direct Growth, shown for context · as of {as_of:%d %b %Y}",
                 fontsize=7.5, color=MUTED, ha="left")
    return fig
