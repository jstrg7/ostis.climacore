/*
 * This source file is part of an OSTIS project. For the latest info, see http://ostis.net
 * Distributed under the MIT License
 * (See accompanying file COPYING.MIT or copy at http://opensource.org/licenses/MIT)
 */

#pragma once

#include <sc-memory/sc_memory.hpp>

#include "data-structures/ConnectorTemplateInfo.hpp"
#include "data-structures/WeightTemplateInfo.hpp"

namespace utils
{
class TemplateUtils
{
public:
  static void GetConnectorTemplateInfo(
      ScMemoryContext & context,
      ScAddr const & connectorTemplateAddr,
      ConnectorTemplateInfo & templateInfo);

  static void GetWeightTemplateInfo(
      ScMemoryContext & context,
      ScAddr const & connectorWeightTemplateAddr,
      WeightTemplateInfo & templateInfo);
};
}  // namespace utils
