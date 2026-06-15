"""Streamlit UI for Camai."""

from pathlib import Path

import streamlit as st

import agent

CLARIFICATION_QUESTIONS = agent.CLARIFICATION_QUESTIONS

st.set_page_config(
    page_title="Camai",
    page_icon="✍️",
    layout="wide",
)

FORM_FIELDS = [
    ("keyword", CLARIFICATION_QUESTIONS[0], "e.g. morning routine for productivity"),
    ("audience", CLARIFICATION_QUESTIONS[1], "e.g. working professionals"),
    ("platform", CLARIFICATION_QUESTIONS[2], "YouTube"),
    ("format", CLARIFICATION_QUESTIONS[3], "long-form video"),
    ("goal", CLARIFICATION_QUESTIONS[4], "Help viewers build a realistic habit"),
]


def init_state():
    defaults = {
        "step": 1,
        "topic": "",
        "clarifications": {},
        "search_plan": [],
        "report": "",
        "report_path": None,
        "drafts": None,
        "script_path": None,
        "viewing_history": False,
        "error": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clarifications_from_form(form_data: dict) -> dict:
    return {
        CLARIFICATION_QUESTIONS[0]: form_data.get("keyword") or "(no preference)",
        CLARIFICATION_QUESTIONS[1]: form_data.get("audience") or "(no preference)",
        CLARIFICATION_QUESTIONS[2]: form_data.get("platform") or "(no preference)",
        CLARIFICATION_QUESTIONS[3]: form_data.get("format") or "(no preference)",
        CLARIFICATION_QUESTIONS[4]: form_data.get("goal") or "(no preference)",
    }


def load_history_into_session(item: dict) -> None:
    path = Path(item["report_path"])
    st.session_state.topic = item["topic"]
    st.session_state.clarifications = item.get("clarifications", {})
    st.session_state.search_plan = item.get("search_queries", [])
    st.session_state.report = agent.load_report(path)
    st.session_state.report_path = path
    st.session_state.drafts = None
    st.session_state.script_path = None
    st.session_state.viewing_history = True
    st.session_state.step = 2


def render_history_sidebar():
    history = agent.list_report_history()
    if not history:
        return

    st.sidebar.subheader("History")
    labels = [f"{item['date']} — {item['topic']}" for item in history]
    selected = st.sidebar.selectbox(
        "Past reports",
        options=range(len(history)),
        format_func=lambda i: labels[i],
        key="history_select",
    )

    if st.sidebar.button("Open report", use_container_width=True):
        load_history_into_session(history[selected])
        st.rerun()


def render_sidebar():
    st.sidebar.title("Camai")
    st.sidebar.caption("Research any topic and draft platform-ready content.")

    status = agent.env_status()
    st.sidebar.subheader("Configuration")
    st.sidebar.write("Anthropic API", "✅" if status["anthropic"] else "❌")
    st.sidebar.write("Tavily API", "✅" if status["tavily"] else "❌")
    st.sidebar.write("Google Sheet", "✅" if status["google_sheet"] else "—")
    st.sidebar.write("Service account", "✅" if status["service_account"] else "—")
    st.sidebar.write(
        "Output length",
        f"{status['output_length']} ({status['output_word_range']} words)",
    )

    if not status["anthropic"] or not status["tavily"]:
        st.sidebar.warning("Add ANTHROPIC_API_KEY and TAVILY_API_KEY to `.env` in the v2 folder.")

    st.sidebar.divider()
    render_history_sidebar()
    st.sidebar.divider()
    if st.sidebar.button("Start over", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def render_step_indicator():
    steps = ["Brief", "Research", "Drafts", "Publish"]
    cols = st.columns(len(steps))
    for idx, (col, label) in enumerate(zip(cols, steps), start=1):
        marker = "●" if st.session_state.step == idx else "○"
        col.markdown(f"{marker} **{idx}. {label}**")


def render_brief_step():
    st.header("Content brief")
    st.write("Tell the agent what you want to create. It works for any niche or platform.")

    with st.form("brief_form"):
        topic = st.text_input(
            "Topic",
            value=st.session_state.topic,
            placeholder="How to batch a week of content in one afternoon",
        )

        st.markdown("#### Creator context")
        cols = st.columns(2)
        form_values = {"topic": topic}

        for idx, (field_key, label, placeholder) in enumerate(FORM_FIELDS):
            with cols[idx % 2]:
                form_values[field_key] = st.text_input(label, placeholder=placeholder)

        submitted = st.form_submit_button("Start research", type="primary", use_container_width=True)

    if submitted:
        if not topic.strip():
            st.error("Enter a topic to continue.")
            return

        st.session_state.topic = topic.strip()
        st.session_state.clarifications = clarifications_from_form(form_values)
        st.session_state.viewing_history = False
        st.session_state.report = ""
        st.session_state.report_path = None
        st.session_state.search_plan = []
        st.session_state.drafts = None
        st.session_state.script_path = None
        st.session_state.step = 2
        st.rerun()


def render_research_step():
    st.header("Research")
    st.write(f"**Topic:** {st.session_state.topic}")

    if st.session_state.viewing_history:
        st.info("Viewing a saved report from history.")

    if not st.session_state.report:
        if st.button("Run research", type="primary"):
            progress = st.progress(0, text="Planning searches...")
            status = st.empty()

            def on_search(query: str, used: int, total: int):
                progress.progress(min(used / total, 1.0), text=f"Searching ({used}/{total}): {query}")
                status.caption(f"Latest query: {query}")

            try:
                with st.spinner("Researching your topic..."):
                    result = agent.run_full_research(
                        st.session_state.topic,
                        st.session_state.clarifications,
                        on_search=on_search,
                    )
                st.session_state.search_plan = result["search_plan"]
                st.session_state.report = result["report"]
                st.session_state.report_path = result["report_path"]
                progress.empty()
                status.empty()
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        return

    if st.session_state.search_plan:
        with st.expander("Search plan", expanded=False):
            for idx, query in enumerate(st.session_state.search_plan, start=1):
                st.write(f"{idx}. {query}")

    st.subheader("Research report")
    st.markdown(st.session_state.report)
    st.caption(f"Saved to `{st.session_state.report_path}`")

    report_path = Path(st.session_state.report_path) if st.session_state.report_path else None
    if report_path and report_path.exists():
        st.download_button(
            "Download report",
            data=report_path.read_text(encoding="utf-8"),
            file_name=report_path.name,
            mime="text/markdown",
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to brief"):
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("Go to drafts", type="primary"):
            st.session_state.step = 3
            st.rerun()


def render_drafts_step():
    st.header("Content drafts")
    st.write(f"**Topic:** {st.session_state.topic}")

    if not st.session_state.drafts:
        existing_path = agent.draft_path_for_topic(st.session_state.topic)
        if existing_path.exists():
            st.info(f"A draft already exists for this topic: `{existing_path.name}`")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Open existing draft", type="primary", use_container_width=True):
                    st.session_state.drafts = agent.load_draft_from_file(existing_path)
                    st.session_state.script_path = existing_path
                    st.rerun()
            with col2:
                if st.button("Open file in editor", use_container_width=True):
                    agent.open_in_editor(existing_path)
            with col3:
                generate_fresh = st.button("Generate fresh draft", use_container_width=True)
            st.caption("Generating a fresh draft will overwrite the existing draft file for this topic.")
        else:
            generate_fresh = st.button("Generate drafts", type="primary")

        if generate_fresh:
            try:
                with st.spinner("Writing scripts and platform copy..."):
                    result = agent.run_full_drafts(
                        st.session_state.topic,
                        st.session_state.report,
                        st.session_state.clarifications,
                    )
                st.session_state.drafts = result["drafts"]
                st.session_state.script_path = result["script_path"]
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        return

    drafts = st.session_state.drafts
    platform = drafts.get("platform", {})
    if not isinstance(platform, dict):
        platform = {}

    with st.expander("Content strategy", expanded=True):
        st.markdown(str(drafts.get("content_strategy", "")))

    script = st.text_area(
        "Script",
        value=drafts.get("script", ""),
        height=260,
    )

    col1, col2 = st.columns(2)
    with col1:
        primary_title = st.text_input("Title", value=platform.get("primary_title", ""))
        thumbnail_text = st.text_input("Thumbnail text", value=platform.get("thumbnail_text", ""))
        short_form = st.text_area("Short-form copy", value=platform.get("short_form", ""), height=120)
    with col2:
        primary_description = st.text_area(
            "Primary description",
            value=platform.get("primary_description", ""),
            height=120,
        )
        social_post = st.text_area("Social post", value=platform.get("social_post", ""), height=120)

    with st.expander("Marketing strategy", expanded=False):
        st.markdown(str(drafts.get("marketing_strategy", "")))

    updated_drafts = dict(drafts)
    updated_drafts["script"] = script
    updated_drafts["platform"] = {
        **platform,
        "primary_title": primary_title,
        "thumbnail_text": thumbnail_text,
        "primary_description": primary_description,
        "short_form": short_form,
        "social_post": social_post,
    }
    st.session_state.drafts = updated_drafts

    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button("Back to research"):
            st.session_state.step = 2
            st.rerun()
    with nav2:
        if st.button("Continue to publish", type="primary"):
            st.session_state.step = 4
            st.rerun()
    with nav3:
        if st.session_state.script_path:
            script_path = Path(st.session_state.script_path)
            if script_path.exists():
                st.download_button(
                    "Download draft",
                    data=script_path.read_text(encoding="utf-8"),
                    file_name=script_path.name,
                    mime="text/markdown",
                    use_container_width=True,
                )

    st.divider()
    with st.expander("Need a different draft?", expanded=False):
        st.caption("Generate a fresh draft from the current research. This overwrites the topic draft file in `output/`.")
        if st.button("Generate fresh draft", key="regenerate_loaded_draft"):
            try:
                with st.spinner("Writing a fresh draft..."):
                    result = agent.run_full_drafts(
                        st.session_state.topic,
                        st.session_state.report,
                        st.session_state.clarifications,
                    )
                st.session_state.drafts = result["drafts"]
                st.session_state.script_path = result["script_path"]
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def render_publish_step():
    st.header("Publish")
    st.write("Push the edited draft to Google Sheets and optionally create a calendar event.")

    status = agent.env_status()
    if not status["google_sheet"] or not status["service_account"]:
        st.info("Google publishing is optional. Set `GOOGLE_SHEET_ID` and add `service-account.json` to enable it.")

    drafts = st.session_state.drafts or {}
    platform = drafts.get("platform", {}) if isinstance(drafts.get("platform"), dict) else {}
    st.markdown(f"**Title:** {platform.get('primary_title', st.session_state.topic)}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to drafts"):
            st.session_state.step = 3
            st.rerun()
    with col2:
        if st.button("Push to Google Sheets", type="primary", disabled=not (
            status["google_sheet"] and status["service_account"]
        )):
            try:
                with st.spinner("Publishing..."):
                    result = agent.publish_drafts(st.session_state.topic, drafts)
                st.success(f"Saved as episode {result['episode_num']}.")
                if result["calendar_url"]:
                    st.link_button("Open calendar event", result["calendar_url"])
            except Exception as exc:
                st.error(str(exc))


def main():
    init_state()
    render_sidebar()
    st.title("Camai")
    render_step_indicator()
    st.divider()

    if st.session_state.step == 1:
        render_brief_step()
    elif st.session_state.step == 2:
        render_research_step()
    elif st.session_state.step == 3:
        render_drafts_step()
    elif st.session_state.step == 4:
        render_publish_step()


if __name__ == "__main__":
    main()
