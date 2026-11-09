package com.acme.billing;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

@AnalyzeClasses(packages = "com.acme.billing")
public class ArchitectureTest {

    /** Garde-fou de la règle « pas de logique métier dans les contrôleurs » (CLAUDE.md, Conventions). */
    @ArchTest
    static final ArchRule controllers_do_not_touch_repositories = noClasses()
            .that().haveSimpleNameEndingWith("Controller")
            .should().dependOnClassesThat().haveSimpleNameEndingWith("Repository");
}
