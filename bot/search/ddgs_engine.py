from duckduckgo_search import DDGS

from bot.config import MAX_SEARCH_RESULTS


def search_web(query):

    results_list = []

    try:

        with DDGS() as ddgs:

            results = ddgs.text(
                keywords=query,
                region="wt-wt",
                safesearch="moderate",
                max_results=MAX_SEARCH_RESULTS
            )

            for result in results:

                title = result.get("title", "")
                body = result.get("body", "")
                href = result.get("href", "")

                clean_result = {
                    "title": title.strip(),
                    "body": body.strip(),
                    "url": href.strip()
                }

                results_list.append(clean_result)

    except Exception as e:

        print(f"[DDGS ERROR]: {e}")

    return results_list
