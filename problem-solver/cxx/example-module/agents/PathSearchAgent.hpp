/*
 * This source file is part of an OSTIS project. For the latest info, see
 * http://ostis.net Distributed under the MIT License (See accompanying file
 * COPYING.MIT or copy at http://opensource.org/licenses/MIT)
 */

#pragma once

#include <sc-memory/sc_agent.hpp>

#include "data-structures/ConnectorTemplateInfo.hpp"
#include "data-structures/WeightTemplateInfo.hpp"
#include "data-structures/PathInfo.hpp"

class PathSearchAgent : public ScActionInitiatedAgent
{
public:
  PathSearchAgent();

  ScAddr GetActionClass() const override;

  ScResult DoProgram(ScAction & action) override;

private:
  ScStructure FormResult(
      PathInfo const & pathInfo,
      ConnectorTemplateInfo const & connectorTemplateInfo,
      WeightTemplateInfo const & weightTemplateInfo) const;

  void AddConnectionIntoStructure(
      ScAddr const & first,
      ScAddr const & second,
      ScAddr const & connector,
      ConnectorTemplateInfo const & connectorTemplateInfo,
      ScStructure & structure) const;

  void AddPathWeightIntoStructure(
      ScAddr const & pathAddr,
      WeightTemplateInfo const & weightTemplateInfo,
      unsigned const length,
      ScStructure & structure) const;
};
