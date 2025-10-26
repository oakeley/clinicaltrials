"""
Module for generating analysis reports with statistics and visualizations.
"""

import logging
from typing import Dict, List, Any
from pathlib import Path
import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
from datetime import datetime


class ReportGenerator:
    """
    Generates comprehensive reports with statistics and visualizations.
    """

    def __init__(self, output_dir: str = "."):
        """
        Initialize report generator.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
        self.figures_dir = self.output_dir / "figures"
        self.figures_dir.mkdir(exist_ok=True)

    def generate_report(self, results_by_disease: Dict[str, List[Dict[str, Any]]],
                       metadata: Dict[str, Any]) -> str:
        """
        Generate comprehensive markdown report with statistics and visualizations.

        Args:
            results_by_disease: Dictionary mapping diseases to trial results
            metadata: Metadata about the analysis

        Returns:
            Path to generated report file
        """
        self.logger.info("Generating analysis report")

        report_lines = []

        report_lines.extend(self._generate_header(metadata))
        report_lines.extend(self._generate_executive_summary(results_by_disease))
        report_lines.extend(self._generate_overall_statistics(results_by_disease))
        report_lines.extend(self._generate_disease_sections(results_by_disease))
        report_lines.extend(self._generate_visualizations_section(results_by_disease))
        report_lines.extend(self._generate_conclusions(results_by_disease))

        report_content = "\n".join(report_lines)

        report_path = self.output_dir / "clinical_trials_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        self.logger.info(f"Report generated: {report_path}")
        return str(report_path)

    def _sanitize_filename(self, text: str) -> str:
        """
        Sanitize text for use in filenames to avoid LaTeX issues.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text safe for filenames and LaTeX
        """
        safe_text = text.lower()
        safe_text = safe_text.replace("'", "")
        safe_text = safe_text.replace('"', "")
        safe_text = safe_text.replace('`', "")
        safe_text = safe_text.replace(' ', '_')
        safe_text = safe_text.replace('/', '_')
        safe_text = safe_text.replace('\\', '_')
        safe_text = safe_text.replace('(', '')
        safe_text = safe_text.replace(')', '')
        safe_text = safe_text.replace('[', '')
        safe_text = safe_text.replace(']', '')
        safe_text = safe_text.replace('{', '')
        safe_text = safe_text.replace('}', '')
        safe_text = safe_text.replace(',', '_')
        safe_text = safe_text.replace('.', '_')
        safe_text = safe_text.replace(':', '_')
        safe_text = safe_text.replace(';', '_')
        safe_text = safe_text.replace('&', '_and_')
        safe_text = safe_text.replace('%', '_pct_')
        safe_text = safe_text.replace('#', '_num_')
        while '__' in safe_text:
            safe_text = safe_text.replace('__', '_')
        safe_text = safe_text.strip('_')
        return safe_text

    def _generate_header(self, metadata: Dict[str, Any]) -> List[str]:
        """
        Generate report header with YAML front matter for pandoc PDF generation.

        Args:
            metadata: Analysis metadata

        Returns:
            List of markdown lines
        """
        lines = [
            "---",
            "documentclass: article",
            "geometry: margin=2cm, top=1.5cm",
            "header-includes:",
            "  - \\usepackage{graphicx}",
            "  - \\usepackage[absolute,overlay]{textpos}",
            "  - \\usepackage{fancyhdr}",
            "  - \\usepackage{lipsum}",
            "  - \\usepackage{tikz}",
            "  - \\usepackage[export]{adjustbox}",
            "  - \\setlength{\\TPHorizModule}{1mm}",
            "  - \\setlength{\\TPVertModule}{1mm}",
            "---",
            "",
            "\\pagestyle{empty}",
            "",
            "# Clinical Trials Analysis Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**Source Data:** {', '.join(metadata.get('source_sheets', []))}",
            "",
            "---",
            ""
        ]
        return lines

    def _generate_executive_summary(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """
        Generate executive summary section.

        Args:
            results_by_disease: Results organized by disease

        Returns:
            List of markdown lines
        """
        total_diseases = len(results_by_disease)
        total_trials = sum(len(trials) for trials in results_by_disease.values())
        total_completed = sum(
            sum(1 for t in trials if t.get('is_complete', False))
            for trials in results_by_disease.values()
        )
        total_with_results = sum(
            sum(1 for t in trials if t.get('has_results', False))
            for trials in results_by_disease.values()
        )

        lines = [
            "## Executive Summary",
            "",
            f"This report analyzes **{total_trials}** clinical trials across **{total_diseases}** diseases.",
            "",
            f"- **Total Trials:** {total_trials}",
            f"- **Completed Trials:** {total_completed} ({100*total_completed/total_trials if total_trials else 0:.1f}%)",
            f"- **Trials with Results:** {total_with_results} ({100*total_with_results/total_trials if total_trials else 0:.1f}%)",
            f"- **Ongoing Trials:** {total_trials - total_completed}",
            "",
            "---",
            ""
        ]
        return lines

    def _generate_overall_statistics(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """
        Generate overall statistics section.

        Args:
            results_by_disease: Results organized by disease

        Returns:
            List of markdown lines
        """
        lines = [
            "## Overall Statistics",
            ""
        ]

        all_trials = [trial for trials in results_by_disease.values() for trial in trials]

        status_counts = {}
        for trial in all_trials:
            status = trial.get('overall_status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        lines.append("### Trial Status Distribution")
        lines.append("")
        for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- **{status}:** {count} trials")
        lines.append("")

        phase_counts = {}
        for trial in all_trials:
            phases = trial.get('phases', [])
            for phase in phases:
                phase_counts[phase] = phase_counts.get(phase, 0) + 1

        if phase_counts:
            lines.append("### Phase Distribution")
            lines.append("")
            for phase, count in sorted(phase_counts.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{phase}:** {count} trials")
            lines.append("")

        durations = [
            t.get('duration', {}).get('months', 0)
            for t in all_trials
            if t.get('duration', {}).get('months') is not None and t.get('duration', {}).get('months', 0) > 0
        ]

        if durations:
            lines.append("### Trial Duration Statistics")
            lines.append("")
            lines.append(f"- **Average Duration:** {np.mean(durations):.1f} months")
            lines.append(f"- **Median Duration:** {np.median(durations):.1f} months")
            lines.append(f"- **Min Duration:** {min(durations):.1f} months")
            lines.append(f"- **Max Duration:** {max(durations):.1f} months")
            lines.append("")

        lines.append("---")
        lines.append("")

        return lines

    def _generate_disease_sections(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """
        Generate detailed sections for each disease with per-disease visualizations.

        Args:
            results_by_disease: Results organized by disease

        Returns:
            List of markdown lines
        """
        lines = [
            "## Disease-Specific Analysis",
            ""
        ]

        for disease, trials in sorted(results_by_disease.items()):
            lines.append(f"### {disease}")
            lines.append("")
            lines.append(f"**Total Trials:** {len(trials)}")
            lines.append("")

            completed = [t for t in trials if t.get('is_complete', False)]
            ongoing = [t for t in trials if not t.get('is_complete', False)]

            lines.append(f"- Completed: {len(completed)}")
            lines.append(f"- Ongoing: {len(ongoing)}")
            lines.append(f"- With Results: {sum(1 for t in trials if t.get('has_results', False))}")
            lines.append("")

            if trials:
                durations = [
                    t.get('duration', {}).get('months', 0)
                    for t in trials
                    if t.get('duration', {}).get('months') is not None and t.get('duration', {}).get('months', 0) > 0
                ]
                if durations:
                    lines.append(f"**Average Trial Duration:** {np.mean(durations):.1f} months")
                    lines.append("")

                fig_status = self._create_disease_status_chart(disease, trials)
                if fig_status:
                    lines.append(f"**Status Distribution:**")
                    lines.append("")
                    lines.append(f"![{disease} Status](figures/{fig_status})")
                    lines.append("")

                fig_phase = self._create_disease_phase_chart(disease, trials)
                if fig_phase:
                    lines.append(f"**Phase Distribution:**")
                    lines.append("")
                    lines.append(f"![{disease} Phases](figures/{fig_phase})")
                    lines.append("")

                top_trials = sorted(trials, key=lambda x: x.get('enrollment', {}).get('count', 0), reverse=True)[:5]
                if top_trials and top_trials[0].get('enrollment', {}).get('count', 0) > 0:
                    lines.append("**Top 5 Trials by Enrollment:**")
                    lines.append("")
                    for trial in top_trials:
                        enrollment = trial.get('enrollment', {}).get('count', 0)
                        if enrollment > 0:
                            nct_id = trial.get('nct_id', '')
                            title = trial.get('brief_title', '')[:80]
                            status = trial.get('overall_status', '')
                            lines.append(f"- **[{nct_id}]({trial.get('url', '')})** ({enrollment:,} participants)")
                            lines.append(f"  - Status: {status}")
                            lines.append(f"  - Title: {title}...")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return lines

    def _generate_visualizations_section(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """
        Generate visualizations and add them to the report.

        Args:
            results_by_disease: Results organized by disease

        Returns:
            List of markdown lines
        """
        lines = [
            "## Visualizations",
            ""
        ]

        fig1_path = self._create_disease_comparison_chart(results_by_disease)
        lines.append("### Trials per Disease")
        lines.append("")
        lines.append(f"![Trials per Disease]({fig1_path})")
        lines.append("")

        fig2_path = self._create_status_distribution_chart(results_by_disease)
        lines.append("### Trial Status Distribution")
        lines.append("")
        lines.append(f"![Trial Status Distribution]({fig2_path})")
        lines.append("")

        fig3_path = self._create_duration_distribution_chart(results_by_disease)
        if fig3_path:
            lines.append("### Trial Duration Distribution")
            lines.append("")
            lines.append(f"![Trial Duration Distribution]({fig3_path})")
            lines.append("")

        fig4_path = self._create_phase_distribution_chart(results_by_disease)
        if fig4_path:
            lines.append("### Phase Distribution")
            lines.append("")
            lines.append(f"![Phase Distribution]({fig4_path})")
            lines.append("")

        lines.append("---")
        lines.append("")

        return lines

    def _create_disease_comparison_chart(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Create bar chart comparing number of trials per disease.

        Args:
            results_by_disease: Results organized by disease

        Returns:
            Path to saved figure
        """
        diseases = list(results_by_disease.keys())[:15]
        trial_counts = [len(results_by_disease[d]) for d in diseases]

        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.barh(diseases, trial_counts, color='steelblue')

        ax.set_xlabel('Number of Trials', fontsize=12)
        ax.set_title('Clinical Trials per Disease', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)

        for i, (disease, count) in enumerate(zip(diseases, trial_counts)):
            ax.text(count, i, f' {count}', va='center', fontsize=10)

        plt.tight_layout()

        fig_path = self.figures_dir / "trials_per_disease.png"
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()

        return f"figures/{fig_path.name}"

    def _create_status_distribution_chart(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Create pie chart of trial status distribution.

        Args:
            results_by_disease: Results organized by disease

        Returns:
            Path to saved figure
        """
        all_trials = [trial for trials in results_by_disease.values() for trial in trials]

        status_counts = {}
        for trial in all_trials:
            status = trial.get('overall_status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        statuses = list(status_counts.keys())
        counts = list(status_counts.values())

        fig, ax = plt.subplots(figsize=(10, 8))
        colors = plt.cm.Set3(range(len(statuses)))
        wedges, texts, autotexts = ax.pie(counts, labels=statuses, autopct='%1.1f%%',
                                           colors=colors, startangle=90)

        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')

        ax.set_title('Trial Status Distribution', fontsize=14, fontweight='bold')

        plt.tight_layout()

        fig_path = self.figures_dir / "status_distribution.png"
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()

        return f"figures/{fig_path.name}"

    def _create_duration_distribution_chart(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Create histogram of trial durations.

        Args:
            results_by_disease: Results organized by disease

        Returns:
            Path to saved figure or None if no duration data
        """
        all_trials = [trial for trials in results_by_disease.values() for trial in trials]

        durations = [
            t.get('duration', {}).get('months', 0)
            for t in all_trials
            if t.get('duration', {}).get('months') is not None and t.get('duration', {}).get('months', 0) > 0
        ]

        if not durations:
            return None

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(durations, bins=20, color='steelblue', edgecolor='black', alpha=0.7)

        ax.set_xlabel('Duration (months)', fontsize=12)
        ax.set_ylabel('Number of Trials', fontsize=12)
        ax.set_title('Distribution of Trial Durations', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        ax.axvline(np.mean(durations), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(durations):.1f} months')
        ax.axvline(np.median(durations), color='green', linestyle='--', linewidth=2, label=f'Median: {np.median(durations):.1f} months')
        ax.legend()

        plt.tight_layout()

        fig_path = self.figures_dir / "duration_distribution.png"
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()

        return f"figures/{fig_path.name}"

    def _create_phase_distribution_chart(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Create bar chart of phase distribution.

        Args:
            results_by_disease: Results organized by disease

        Returns:
            Path to saved figure or None if no phase data
        """
        all_trials = [trial for trials in results_by_disease.values() for trial in trials]

        phase_counts = {}
        for trial in all_trials:
            phases = trial.get('phases', [])
            for phase in phases:
                phase_counts[phase] = phase_counts.get(phase, 0) + 1

        if not phase_counts:
            return None

        phases = list(phase_counts.keys())
        counts = list(phase_counts.values())

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(phases, counts, color='steelblue', edgecolor='black', alpha=0.7)

        ax.set_ylabel('Number of Trials', fontsize=12)
        ax.set_xlabel('Phase', fontsize=12)
        ax.set_title('Distribution by Trial Phase', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(count)}', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()

        fig_path = self.figures_dir / "phase_distribution.png"
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()

        return f"figures/{fig_path.name}"

    def _generate_conclusions(self, results_by_disease: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """
        Generate conclusions section.

        Args:
            results_by_disease: Results organized by disease

        Returns:
            List of markdown lines
        """
        all_trials = [trial for trials in results_by_disease.values() for trial in trials]

        completed_trials = [t for t in all_trials if t.get('is_complete', False)]
        trials_with_results = [t for t in all_trials if t.get('has_results', False)]

        lines = [
            "## Key Findings",
            ""
        ]

        if all_trials:
            completion_rate = 100 * len(completed_trials) / len(all_trials)
            results_rate = 100 * len(trials_with_results) / len(all_trials)

            lines.append(f"1. **Completion Rate:** {completion_rate:.1f}% of trials have been completed")
            lines.append(f"2. **Results Availability:** {results_rate:.1f}% of trials have published results")
            lines.append("")

            disease_with_most_trials = max(results_by_disease.items(), key=lambda x: len(x[1]))
            lines.append(f"3. **Most Studied Disease:** {disease_with_most_trials[0]} "
                        f"({len(disease_with_most_trials[1])} trials)")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(f"*Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*")
        lines.append("")

        return lines

    def _create_disease_status_chart(self, disease: str, trials: List[Dict[str, Any]]) -> str:
        """
        Create status distribution chart for a specific disease.

        Args:
            disease: Disease name
            trials: List of trials for this disease

        Returns:
            Filename of saved figure
        """
        status_counts = {}
        for trial in trials:
            status = trial.get('overall_status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        if not status_counts:
            return None

        statuses = list(status_counts.keys())
        counts = list(status_counts.values())

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(statuses, counts, color='steelblue', edgecolor='black', alpha=0.7)

        ax.set_ylabel('Number of Trials', fontsize=12)
        ax.set_title(f'{disease} - Trial Status Distribution', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')

        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(count)}', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()

        safe_disease = self._sanitize_filename(disease)
        fig_path = self.figures_dir / f"{safe_disease}_status.png"
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()

        return fig_path.name

    def _create_disease_phase_chart(self, disease: str, trials: List[Dict[str, Any]]) -> str:
        """
        Create phase distribution chart for a specific disease.

        Args:
            disease: Disease name
            trials: List of trials for this disease

        Returns:
            Filename of saved figure
        """
        phase_counts = {}
        for trial in trials:
            phases = trial.get('phases', [])
            for phase in phases:
                phase_counts[phase] = phase_counts.get(phase, 0) + 1

        if not phase_counts:
            return None

        phases = list(phase_counts.keys())
        counts = list(phase_counts.values())

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(phases, counts, color='coral', edgecolor='black', alpha=0.7)

        ax.set_ylabel('Number of Trials', fontsize=12)
        ax.set_title(f'{disease} - Phase Distribution', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')

        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(count)}', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()

        safe_disease = self._sanitize_filename(disease)
        fig_path = self.figures_dir / f"{safe_disease}_phases.png"
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()

        return fig_path.name
