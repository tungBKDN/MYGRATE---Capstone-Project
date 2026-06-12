import re

compile_output = """
[ERROR] /D:/capstone_project/MYGRATE---Capstone-Project/working/sonar-stash/src/main/java/org/sonar/plugins/stash/StashPluginConfiguration.java:[67,18] cannot find symbol
  symbol:   method getURL()
  location: variable server of type org.sonar.api.platform.Server
[ERROR] /D:/capstone_project/MYGRATE---Capstone-Project/working/sonar-stash/src/main/java/org/sonar/plugins/stash/issue/MarkdownPrinter.java:[107,99] cannot find symbol
  symbol:   method toMultimap(PostJobIss[...]leKey,java.util.function.Function<java.lang.Object,java.lang.Object>,ArrayListM[...]reate)
  location: class com.google.common.collect.Multimaps
[ERROR] /D:/capstone_project/MYGRATE---Capstone-Project/working/sonar-stash/src/main/java/org/sonar/plugins/stash/StashIssueReportingPostJob.java:[67,72] cannot find symbol
  symbol:   method issues()
  location: variable context of type org.sonar.api.batch.postjob.PostJobContext
"""

err_pattern = r'((?:src[/\\\\][\\w./-]+\\.java)|[A-Z]:[/\\\\][\\w./\\\\-]+\\.java)[:\\[](\\d+)(?:,\\d+)?\\]?:?\\s+(?:error:\\s+)?(.+)'

print("Running regex finditer...")
found = False
for match in re.finditer(err_pattern, compile_output):
    found = True
    print(f"Match: {match.groups()}")

if not found:
    print("No match found!")
