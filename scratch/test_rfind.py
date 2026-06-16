import re

pom_content = """<?xml version='1.0' encoding='UTF-8'?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.sonar</groupId>
  <artifactId>sonar-stash-plugin</artifactId>
  <version>1.7.0-SNAPSHOT</version>
  <packaging>sonar-plugin</packaging>
  <description>Integration between Atlassian Stash (BitBucket) and SonarQube</description>
  <name>Stash</name>
  <url>https://github.com/AmadeusITGroup/sonar-stash</url>
  <licenses>
    <license>
      <name>MIT</name>
      <url>https://opensource.org/licenses/MIT</url>
      <distribution>repo</distribution>
    </license>
  </licenses>
  <scm>
    <connection>scm:git:git@github.com:AmadeusITGroup/sonar-stash.git</connection>
    <developerConnection>scm:git:git@github.com:AmadeusITGroup/sonar-stash.git</developerConnection>
    <url>https://github.com/AmadeusITGroup/sonar-stash</url>
    <tag>HEAD</tag>
  </scm>
  <issueManagement>
    <system>GitHub Issues</system>
    <url>https://github.com/AmadeusITGroup/sonar-stash/issues</url>
  </issueManagement>
  <ciManagement>
    <system>Travis</system>
    <url>https://travis-ci.org/AmadeusITGroup/sonar-stash</url>
  </ciManagement>
  <properties>
    <sonar.version>6.7</sonar.version>
    <sonar.pluginName>Stash</sonar.pluginName>
    <sonar.pluginClass>org.sonar.plugins.stash.StashPlugin</sonar.pluginClass>
    <project.reporting.outputEncoding>UTF-8</project.reporting.outputEncoding>
    <test.sonarqube.dist.groupId>fixme.fixme</test.sonarqube.dist.groupId>
    <test.sonarqube.dist.artifactId>sonarqube-dist</test.sonarqube.dist.artifactId>
    <test.sonarqube.dist.version>7.6</test.sonarqube.dist.version>
    <test.sonarqube.dist.outputdir>${project.build.directory}/fixtures/sonarqube</test.sonarqube.dist.outputdir>
    <test.sonarscanner.dist.groupId>fixme.fixme</test.sonarscanner.dist.groupId>
    <test.sonarscanner.dist.artifactId>sonarscanner-dist</test.sonarscanner.dist.artifactId>
    <test.sonarscanner.dist.version>3.3.0.1492</test.sonarscanner.dist.version>
    <test.sonarscanner.dist.outputdir>${project.build.directory}/fixtures/sonarscanner</test.sonarscanner.dist.outputdir>
    <test.url.binaries.repo>https://binaries.sonarsource.com/Distribution</test.url.binaries.repo>
    <test.plugin.archive>${project.build.directory}/${project.artifactId}-${project.version}.jar</test.plugin.archive>
    <test.sources.dir>${project.build.directory}/fixtures/sources</test.sources.dir>
    <sonar.coverage.exclusions>src/main/java/org/sonar/plugins/stash/StashPlugin.java,src/main/java/org/sonar/plugins/stash/StashPluginConfiguration.java</sonar.coverage.exclusions>
    <maven.compiler.source>17</maven.compiler.source>
    <maven.compiler.target>17</maven.compiler.target>
  </properties>
  <organization>
    <name>Amadeus</name>
    <url>http://www.amadeus.com</url>
  </organization>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>org.junit</groupId>
        <artifactId>junit-bom</artifactId>
        <version>5.4.0</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>
    </dependencies>
  </dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.sonarsource.sonarqube</groupId>
      <artifactId>sonar-plugin-api</artifactId>
      <version>9.3.0.51899</version>
      <scope>provided</scope>
    </dependency>
"""

lines_before = pom_content.splitlines()
start = 71
end = 71
ver = "8.9.10.61524"
replacement = "      <version>8.9.10.61524</version>"

context_start = max(0, start - 10)
context_end = min(len(lines_before), end + 10)
context = "\\n".join(lines_before[context_start:context_end]) + "\\n" + replacement

print(f"Context slice lines {context_start+1} to {context_end}:")
print("---")
print("\\n".join(lines_before[context_start:context_end]))
print("---")

gid_match = re.search(r"<groupId>([^<]+)</groupId>", context)
aid_match = re.search(r"<artifactId>([^<]+)</artifactId>", context)
print(f"gid_match: {gid_match.group(1) if gid_match else None}")
print(f"aid_match: {aid_match.group(1) if aid_match else None}")

version_str = f"<version>{ver}</version>"
version_idx = context.find(version_str)
print(f"version_str: '{version_str}', found at index {version_idx}")

last_dep = context.rfind("<dependency>", 0, version_idx) if version_idx != -1 else -1
last_plugin = context.rfind("<plugin>", 0, version_idx) if version_idx != -1 else -1

print(f"last_dep index: {last_dep}")
print(f"last_plugin index: {last_plugin}")

is_plugin = (last_plugin > last_dep)
print(f"is_plugin: {is_plugin}")
