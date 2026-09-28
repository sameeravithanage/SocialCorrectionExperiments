require(tidyverse)
require(R6)


RAW_LIVE_DATA_FILE_FACTCHECK_1 <- "/home/sameera/Projects/PhData/2Exp/bin/exp2live1.json";
RAW_TEST_DATA_FILE_FACTCHECK_1 <- "/home/sameera/Projects/PhData/2Exp/bin/testData/exp2test2.json";

FactCheckDataV1 = R6Class(
  classname = "FactCheckDataV1",
  lock_objects = FALSE,
  portable = FALSE,
  
  public = list(
    completed = NULL,
    demographics = NULL,
    excluded = NULL,
    raw = NULL,
    trials = NULL,    
    
    initialize = function(dataFileName, isTestData = FALSE) {
      if (endsWith(dataFileName, ".json")) {
        jsonData <- read_json(dataFileName, flatten = FALSE, simplifyVector = FALSE, simplifyDataFrame = FALSE, simplifyMatrix = FALSE);
        self$raw <- bind_rows(jsonData[[1]])
      }
      else {
        self$raw <- read_csv(dataFileName, col_types = cols(.default = col_character()))
      }
      
      ## Add a column which captures whether a participant finished.
      self$raw$finished <-! is.na(raw$experimentEndTime);
      
      ## The uid for any participants for whom we have reason to
      ## believe should be excluded, are captured here.
      ##
      ## Replace xxx with list of UIDs to exclude
      self$excluded <- c("xxx")

      if (! isTestData) {
        ## Filter out any cases where there is no student or worker id
        ## and cases where there is no record of consent being given.
        included <- self$raw %>% 
          filter(src %in% c("mt", "uoarsp")) %>%
          filter(! is.na(consent_endTime_1))
      }
      else {
        included <- self$raw
      }
      
      self$completed <-
        included[included$finished &  !(included$uid %in% excluded),] %>%
        mutate(uid = as.factor(uid))
      
      politicalLevels = c("soc", 
                          "strongLib","modLib", "slightLib", 
                          "anarch", "middle", "none", "libert", 
                          "slightCons", "modCons", "strongCons")
      
      politics <- completed$demographics_politics
      politics <- ifelse(is.na(politics),"none",politics)
      politics <- ifelse(politics == "na", "none", politics)
      
      self$demographics <- completed %>% 
        dplyr::select(uid, condition, starts_with("demographics")) %>%
        mutate(condition = as.factor(condition),
               age = as.numeric(demographics_age),
               country = as.factor(demographics_country),
               fluency = as.factor(demographics_fluency),
               politics = factor(politics, levels = politicalLevels),                        
               education = as.factor(demographics_education),         
               socialMedia = as.factor(demographics_socialMedia),                  
               gender = as.factor(demographics_gender)) %>%
        dplyr::select(-starts_with("demographics"))
    
      fixName <- Vectorize(function(name) paste0("FactCheck_T-",paste0(str_match(name, "(FactCheck_T)-(.+)_enterState_(.+)")[c(3,4)], collapse="_")))

      t1 <- self$completed %>% 
        select(uid, src, condition, starts_with("FactCheck_T-")) %>%
        rename_with(fixName, contains("_enterState_")) %>%
        pivot_longer(cols = starts_with("FactCheck_"),
                     names_to = c("dummy","trialType",".value"),
                     names_pattern = "(FactCheck_T)-(.+)_(.+)",
                     values_to = "value") %>%
        filter(!is.na(trialEndTime)) %>%
        mutate(duration = as.integer(trialEndTime) - as.integer(trialStartTime),
               groundTruth = as.logical(groundTruth),
               trialType = as.factor(mainHeadline),
               trialIndex = as.integer(index),
               prior = as.integer(`slider-pre`),
               share = as.integer(`slider-share`)) %>%
        select(-dummy, -starts_with("slider"), ends_with("-start")) 

      t2 <- t1 %>%
        inner_join(demographics, by = c("uid", "condition")) %>%
        group_by(uid) %>%
        mutate(numTrials = n(), priorRank = rank(prior), shareRank = rank(share))
      
      self$means <- 
        t2 %>%
        group_by(trialType) %>%
        summarise(meanPrior = mean(prior), meanShare = mean(share)) %>%
        mutate(orderByPrior = rank(meanPrior), orderByShare = rank(meanShare)) 
      
      trialTypeLevels <- levels(reorder(self$means$trialType, self$means$orderByPrior))

      self$trials <- t2 %>% mutate(trialType = factor(trialType, levels = trialTypeLevels)) %>% ungroup()
    }
  )
)

getFactCheckTestDataV1 = function() {
  FactCheckDataV1$new(RAW_LIVE_DATA_FILE_FACTCHECK_1, isTestData = FALSE)
}
